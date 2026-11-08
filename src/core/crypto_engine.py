"""Cryptographic operations built on the maintained ``cryptography`` package and the stdlib.

* Encryption: AES-GCM (authenticated). Password mode derives a 256-bit key with
  PBKDF2-HMAC-SHA256 from a fresh random salt; every message also gets a fresh random
  96-bit nonce, so a (key, nonce) pair is never reused.
* Hashing / HMAC: hashlib / hmac (SHA-256, SHA-512).
* Hashing is NOT encryption and Base64/hex are NOT encryption (they are encodings).

Everything is local; nothing here touches the network.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import unicodedata

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.models.crypto_envelope import (CIPHERS, KDF_NONE, KDF_PBKDF2, MAX_ITERATIONS, MIN_ITERATIONS,
                                        NONCE_LEN, SALT_LEN, CryptoEnvelope, EnvelopeError)

DEFAULT_ITERATIONS = 600_000
MAX_PLAINTEXT_BYTES = 16 * 1024 * 1024
HASH_ALGORITHMS = {"SHA-256": "sha256", "SHA-512": "sha512"}


class CryptoError(ValueError):
    """Invalid parameters for a cryptographic operation."""


class DecryptionError(Exception):
    """Authentication failed: wrong password/key or modified data (deliberately not distinguished)."""


_seen_nonces: set[bytes] = set()


def generate_salt(length: int = SALT_LEN) -> bytes:
    return secrets.token_bytes(length)


def generate_nonce() -> bytes:
    """Fresh random 96-bit nonce for AES-GCM."""
    return secrets.token_bytes(NONCE_LEN)


def _fresh_nonce(key: bytes) -> bytes:
    """Random nonce with an in-process uniqueness guard per key."""
    tag = hashlib.sha256(key).digest()[:8]
    for _ in range(8):
        nonce = generate_nonce()
        if tag + nonce not in _seen_nonces:
            if len(_seen_nonces) > 200_000:
                _seen_nonces.clear()
            _seen_nonces.add(tag + nonce)
            return nonce
    raise CryptoError("Could not obtain a unique nonce.")  # astronomically unlikely


def hash_bytes(data: bytes, algorithm: str = "SHA-256") -> bytes:
    if algorithm not in HASH_ALGORITHMS:
        raise CryptoError(f"Unsupported hash algorithm: {algorithm}")
    return hashlib.new(HASH_ALGORITHMS[algorithm], data).digest()


def hmac_digest(key: bytes, data: bytes, algorithm: str = "SHA-256") -> bytes:
    if algorithm not in HASH_ALGORITHMS:
        raise CryptoError(f"Unsupported hash algorithm: {algorithm}")
    if not key:
        raise CryptoError("HMAC key must not be empty.")
    return hmac.new(key, data, HASH_ALGORITHMS[algorithm]).digest()


def hmac_verify(key: bytes, data: bytes, tag: bytes, algorithm: str = "SHA-256") -> bool:
    """Constant-time comparison of an HMAC tag."""
    return hmac.compare_digest(hmac_digest(key, data, algorithm), tag)


def _password_bytes(password: str) -> bytes:
    if not password:
        raise CryptoError("Password must not be empty.")
    return unicodedata.normalize("NFC", password).encode("utf-8")


def pbkdf2_derive(password: str, salt: bytes, iterations: int = DEFAULT_ITERATIONS, length: int = 32) -> bytes:
    """PBKDF2-HMAC-SHA256 key derivation (password is NFC-normalised, then UTF-8 encoded)."""
    if not (MIN_ITERATIONS <= iterations <= MAX_ITERATIONS):
        raise CryptoError(f"Iterations must be between {MIN_ITERATIONS:,} and {MAX_ITERATIONS:,}.")
    if len(salt) < SALT_LEN:
        raise CryptoError(f"Salt must be at least {SALT_LEN} bytes.")
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=length, salt=salt, iterations=iterations).derive(
        _password_bytes(password))


def _check_plaintext(plaintext: bytes) -> None:
    if len(plaintext) > MAX_PLAINTEXT_BYTES:
        raise CryptoError(f"Plaintext too large ({len(plaintext):,} > {MAX_PLAINTEXT_BYTES:,} bytes).")


def _seal(key: bytes, plaintext: bytes, cipher: str, kdf: str, iterations: int, salt: bytes) -> CryptoEnvelope:
    nonce = _fresh_nonce(key)
    draft = CryptoEnvelope(cipher, kdf, iterations, salt, nonce, b"")
    ct = AESGCM(key).encrypt(nonce, plaintext, draft.header_bytes())
    return CryptoEnvelope(cipher, kdf, iterations, salt, nonce, ct)


def encrypt_with_password(plaintext: bytes, password: str, *, iterations: int = DEFAULT_ITERATIONS) -> CryptoEnvelope:
    """AES-256-GCM with a PBKDF2-derived key and fresh salt + nonce."""
    _check_plaintext(plaintext)
    salt = generate_salt()
    key = pbkdf2_derive(password, salt, iterations)
    return _seal(key, plaintext, "AES-256-GCM", KDF_PBKDF2, iterations, salt)


def encrypt_with_key(plaintext: bytes, key: bytes) -> CryptoEnvelope:
    """AES-GCM with a raw 128/192/256-bit key (random 96-bit nonce per message)."""
    _check_plaintext(plaintext)
    names = {v: k for k, v in CIPHERS.items()}
    if len(key) not in names:
        raise CryptoError(f"AES key must be 16, 24 or 32 bytes (got {len(key)}).")
    return _seal(key, plaintext, names[len(key)], KDF_NONE, 0, b"")


def _open(env: CryptoEnvelope, key: bytes) -> bytes:
    try:
        # AESGCM verifies the authentication tag before returning any plaintext.
        return AESGCM(key).decrypt(env.nonce, env.ciphertext, env.header_bytes())
    except InvalidTag:
        raise DecryptionError("Decryption failed: wrong password/key, or the data was modified.") from None


def decrypt_with_password(env: CryptoEnvelope, password: str) -> bytes:
    if env.kdf != KDF_PBKDF2:
        raise CryptoError("This container is not password-based; supply a raw key instead.")
    return _open(env, pbkdf2_derive(password, env.salt, env.iterations))


def decrypt_with_key(env: CryptoEnvelope, key: bytes) -> bytes:
    if env.kdf != KDF_NONE:
        raise CryptoError("This container is password-based; supply the password instead.")
    if len(key) != CIPHERS[env.cipher]:
        raise CryptoError(f"{env.cipher} needs a {CIPHERS[env.cipher]}-byte key (got {len(key)}).")
    return _open(env, key)


def decrypt_json(text: str, *, password: str | None = None, key: bytes | None = None) -> bytes:
    """Parse, validate and decrypt a CipherLab Pro container."""
    env = CryptoEnvelope.from_json(text)
    if env.kdf == KDF_PBKDF2:
        if password is None:
            raise CryptoError("This container needs a password.")
        return decrypt_with_password(env, password)
    if key is None:
        raise CryptoError("This container needs a raw key (hex).")
    return decrypt_with_key(env, key)


__all__ = ["CryptoError", "DecryptionError", "EnvelopeError", "encrypt_with_password", "encrypt_with_key",
           "decrypt_with_password", "decrypt_with_key", "decrypt_json", "hash_bytes", "hmac_digest",
           "hmac_verify", "pbkdf2_derive", "generate_salt", "generate_nonce"]
