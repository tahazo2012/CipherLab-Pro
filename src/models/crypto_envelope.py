"""Versioned, validated container for encrypted data (format "CipherLabPro" v1).

JSON layout::

    {"format": "CipherLabPro", "version": 1, "cipher": "AES-256-GCM",
     "kdf": "PBKDF2-HMAC-SHA256" | "none", "iterations": 600000,
     "salt": "<base64>", "nonce": "<base64 12 bytes>", "ciphertext": "<base64, tag appended>"}

The header (everything except ``ciphertext``) is bound to the ciphertext as AES-GCM
associated data, so tampering with any header field makes decryption fail.
"""
from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass

FORMAT_NAME = "CipherLabPro"
FORMAT_VERSION = 1
KDF_PBKDF2 = "PBKDF2-HMAC-SHA256"
KDF_NONE = "none"
CIPHERS = {"AES-128-GCM": 16, "AES-192-GCM": 24, "AES-256-GCM": 32}
NONCE_LEN = 12
TAG_LEN = 16
SALT_LEN = 16
MIN_ITERATIONS = 100_000
MAX_ITERATIONS = 5_000_000
MAX_ENVELOPE_CHARS = 40_000_000
_FIELDS = {"format", "version", "cipher", "kdf", "iterations", "salt", "nonce", "ciphertext"}


class EnvelopeError(ValueError):
    """The encrypted-data container is malformed, unsupported or exceeds limits."""


def _b64(value: object, name: str, *, min_len: int, max_len: int) -> bytes:
    if not isinstance(value, str):
        raise EnvelopeError(f"Field '{name}' must be a Base64 string.")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise EnvelopeError(f"Field '{name}' is not valid Base64.") from None
    if not (min_len <= len(raw) <= max_len):
        raise EnvelopeError(f"Field '{name}' has invalid length {len(raw)} (allowed {min_len}-{max_len}).")
    return raw


@dataclass(frozen=True)
class CryptoEnvelope:
    cipher: str
    kdf: str
    iterations: int
    salt: bytes
    nonce: bytes
    ciphertext: bytes
    version: int = FORMAT_VERSION

    def header_bytes(self) -> bytes:
        """Canonical authenticated header (used as AES-GCM associated data)."""
        header = {
            "app": FORMAT_NAME, "v": self.version, "cipher": self.cipher, "kdf": self.kdf,
            "iter": self.iterations, "salt": base64.b64encode(self.salt).decode(),
            "nonce": base64.b64encode(self.nonce).decode(),
        }
        return json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps({
            "format": FORMAT_NAME, "version": self.version, "cipher": self.cipher, "kdf": self.kdf,
            "iterations": self.iterations, "salt": base64.b64encode(self.salt).decode(),
            "nonce": base64.b64encode(self.nonce).decode(),
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
        }, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "CryptoEnvelope":
        if len(text) > MAX_ENVELOPE_CHARS:
            raise EnvelopeError("Encrypted data is larger than the supported limit.")
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EnvelopeError(f"Not a valid CipherLab Pro container (JSON error: {exc.msg}).") from None
        if not isinstance(obj, dict):
            raise EnvelopeError("Container must be a JSON object.")
        if obj.get("format") != FORMAT_NAME:
            raise EnvelopeError("Not a CipherLab Pro container (missing or wrong 'format').")
        if obj.get("version") != FORMAT_VERSION or isinstance(obj.get("version"), bool):
            raise EnvelopeError(f"Unsupported container version {obj.get('version')!r}; this build reads version {FORMAT_VERSION}.")
        extra, missing = set(obj) - _FIELDS, _FIELDS - set(obj)
        if missing:
            raise EnvelopeError(f"Missing field(s): {', '.join(sorted(missing))}.")
        if extra:
            raise EnvelopeError(f"Unknown field(s): {', '.join(sorted(extra))}.")
        cipher, kdf, iters = obj["cipher"], obj["kdf"], obj["iterations"]
        if cipher not in CIPHERS:
            raise EnvelopeError(f"Unsupported cipher {cipher!r}.")
        if kdf not in (KDF_PBKDF2, KDF_NONE):
            raise EnvelopeError(f"Unsupported key-derivation function {kdf!r}.")
        if not isinstance(iters, int) or isinstance(iters, bool):
            raise EnvelopeError("Field 'iterations' must be an integer.")
        if kdf == KDF_PBKDF2:
            if not (MIN_ITERATIONS <= iters <= MAX_ITERATIONS):
                raise EnvelopeError(f"PBKDF2 iterations {iters:,} outside the allowed range {MIN_ITERATIONS:,}-{MAX_ITERATIONS:,}.")
            if cipher != "AES-256-GCM":
                raise EnvelopeError("Password-based containers must use AES-256-GCM.")
            salt = _b64(obj["salt"], "salt", min_len=SALT_LEN, max_len=64)
        else:
            if iters != 0:
                raise EnvelopeError("Containers without a KDF must have iterations = 0.")
            salt = _b64(obj["salt"], "salt", min_len=0, max_len=0)
        nonce = _b64(obj["nonce"], "nonce", min_len=NONCE_LEN, max_len=NONCE_LEN)
        ct = _b64(obj["ciphertext"], "ciphertext", min_len=TAG_LEN, max_len=MAX_ENVELOPE_CHARS)
        return cls(cipher, kdf, iters, salt, nonce, ct)
