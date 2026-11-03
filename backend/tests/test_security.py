import time

import jwt
import pytest

from app import security


def test_password_hash_verifies_only_the_right_password():
    h = security.hash_password("tajne")
    assert h != "tajne"
    assert security.verify_password(h, "tajne")
    assert not security.verify_password(h, "ine")
    assert not security.verify_password("nie-je-hash", "tajne")


def test_token_roundtrip():
    claims = security.decode_token(security.create_token("admin", "admin"))
    assert (claims["sub"], claims["role"]) == ("admin", "admin")


def test_expired_token_is_rejected():
    old = jwt.encode({"sub": "a", "role": "admin", "exp": int(time.time()) - 10}, "test-jwt-secret", algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        security.decode_token(old)


def test_token_signed_with_other_key_is_rejected():
    forged = jwt.encode({"sub": "a", "role": "admin", "exp": int(time.time()) + 60}, "iny", algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        security.decode_token(forged)


def test_pseudonym_is_stable_and_depends_on_prefix():
    assert security.pseudonymize("P01", "p") == security.pseudonymize("P01", "p")
    assert security.pseudonymize("P01", "p") != security.pseudonymize("P02", "p")
    assert security.pseudonymize("P01", "p").startswith("p_")


def test_missing_secret_raises(monkeypatch):
    monkeypatch.delenv("PSEUDO_KEY")
    with pytest.raises(RuntimeError):
        security.pseudonymize("P01", "p")
