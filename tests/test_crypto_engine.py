import json

import pytest

from src.core import crypto_engine as ce
from src.models.crypto_envelope import CryptoEnvelope, EnvelopeError

IT = 100_000


def test_hash_known_vectors():
    assert ce.hash_bytes(b"abc", "SHA-256").hex() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert ce.hash_bytes(b"abc", "SHA-512").hex().startswith("ddaf35a193617aba")


def test_hmac_rfc4231_case1_and_verify():
    tag = ce.hmac_digest(b"\x0b" * 20, b"Hi There", "SHA-256")
    assert tag.hex() == "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"
    assert ce.hmac_verify(b"\x0b" * 20, b"Hi There", tag)
    assert not ce.hmac_verify(b"\x0b" * 20, b"Hi there", tag)


def test_pbkdf2_matches_hashlib():
    import hashlib
    salt = b"s" * 16
    assert ce.pbkdf2_derive("pw", salt, IT) == hashlib.pbkdf2_hmac("sha256", b"pw", salt, IT, 32)


def test_password_round_trip_persian_and_unicode():
    plain = "این یک پیام محرمانه است 😀 hello".encode()
    env = ce.encrypt_with_password(plain, "گذرواژه-قوی", iterations=IT)
    assert ce.decrypt_json(env.to_json(), password="گذرواژه-قوی") == plain


def test_empty_plaintext_round_trip():
    env = ce.encrypt_with_password(b"", "pw", iterations=IT)
    assert ce.decrypt_with_password(env, "pw") == b""


def test_wrong_password_fails_safely():
    env = ce.encrypt_with_password(b"secret", "right", iterations=IT)
    with pytest.raises(ce.DecryptionError):
        ce.decrypt_with_password(env, "wrong")


def test_tampered_ciphertext_and_header_fail():
    env = ce.encrypt_with_password(b"secret data", "pw", iterations=IT)
    obj = json.loads(env.to_json())
    ct = bytearray(env.ciphertext)
    ct[0] ^= 1
    bad = CryptoEnvelope(env.cipher, env.kdf, env.iterations, env.salt, env.nonce, bytes(ct))
    with pytest.raises(ce.DecryptionError):
        ce.decrypt_with_password(bad, "pw")
    obj["iterations"] = IT + 1
    with pytest.raises(ce.DecryptionError):
        ce.decrypt_json(json.dumps(obj), password="pw")


def test_key_mode_round_trip_and_nonce_uniqueness():
    key = bytes(range(32))
    nonces = set()
    for _ in range(2000):
        env = ce.encrypt_with_key(b"x", key)
        nonces.add(env.nonce)
    assert len(nonces) == 2000
    assert ce.decrypt_json(env.to_json(), key=key) == b"x"
    for size in (16, 24):
        e = ce.encrypt_with_key(b"abc", bytes(size))
        assert ce.decrypt_with_key(e, bytes(size)) == b"abc"
    with pytest.raises(ce.CryptoError):
        ce.encrypt_with_key(b"abc", b"short")


def test_fresh_salt_and_nonce_each_time():
    a = ce.encrypt_with_password(b"m", "pw", iterations=IT)
    b = ce.encrypt_with_password(b"m", "pw", iterations=IT)
    assert a.salt != b.salt and a.nonce != b.nonce and a.ciphertext != b.ciphertext


def test_resource_limits():
    with pytest.raises(ce.CryptoError):
        ce.pbkdf2_derive("pw", b"s" * 16, 10)
    with pytest.raises(ce.CryptoError):
        ce.pbkdf2_derive("pw", b"s" * 16, 10**9)
    with pytest.raises(ce.CryptoError):
        ce.encrypt_with_password(b"x" * (ce.MAX_PLAINTEXT_BYTES + 1), "pw", iterations=IT)
    with pytest.raises(ce.CryptoError):
        ce.encrypt_with_password(b"x", "", iterations=IT)


@pytest.fixture
def good():
    return json.loads(ce.encrypt_with_password(b"data", "pw", iterations=IT).to_json())


@pytest.mark.parametrize("mutate,match", [
    (lambda o: o.update(version=2), "version"),
    (lambda o: o.update(format="Other"), "format"),
    (lambda o: o.update(cipher="ROT13"), "cipher"),
    (lambda o: o.update(kdf="md5"), "key-derivation"),
    (lambda o: o.update(iterations=10), "iterations"),
    (lambda o: o.update(iterations=10**9), "iterations"),
    (lambda o: o.update(iterations="600000"), "integer"),
    (lambda o: o.update(nonce="AAAA"), "nonce"),
    (lambda o: o.update(salt="!!!"), "Base64"),
    (lambda o: o.update(ciphertext="AAAA"), "ciphertext"),
    (lambda o: o.update(extra=1), "Unknown"),
    (lambda o: o.pop("salt"), "Missing"),
])
def test_invalid_metadata_rejected(good, mutate, match):
    mutate(good)
    with pytest.raises(EnvelopeError, match=match):
        CryptoEnvelope.from_json(json.dumps(good))


def test_non_json_and_wrong_type_rejected():
    for text in ("not json", "[]", "123"):
        with pytest.raises(EnvelopeError):
            CryptoEnvelope.from_json(text)


def test_mode_mismatch_errors():
    pw_env = ce.encrypt_with_password(b"a", "pw", iterations=IT)
    with pytest.raises(ce.CryptoError):
        ce.decrypt_with_key(pw_env, bytes(32))
    key_env = ce.encrypt_with_key(b"a", bytes(32))
    with pytest.raises(ce.CryptoError):
        ce.decrypt_with_password(key_env, "pw")
