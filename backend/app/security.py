"""Heslá, JWT tokeny a pseudonymizácia identifikátorov."""
import hashlib
import hmac
import os
import time

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

TOKEN_TTL_S = 8 * 3600

_hasher = PasswordHasher()


def _secret(name: str) -> bytes:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Chýba premenná prostredia {name}")
    return value.encode()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_token(username: str, role: str) -> str:
    claims = {"sub": username, "role": role, "exp": int(time.time()) + TOKEN_TTL_S}
    return jwt.encode(claims, _secret("JWT_SECRET"), algorithm="HS256")


def decode_token(token: str) -> dict:
    """Vyhodí jwt.PyJWTError pri neplatnom alebo expirovanom tokene."""
    return jwt.decode(token, _secret("JWT_SECRET"), algorithms=["HS256"])


def pseudonymize(value: str, prefix: str) -> str:
    """Stabilný pseudonym: rovnaký vstup dá rovnaký výstup, spätne sa nedá odvodiť bez PSEUDO_KEY."""
    digest = hmac.new(_secret("PSEUDO_KEY"), value.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{prefix}_{digest}"


def ingest_key_ok(candidate: str | None) -> bool:
    expected = os.environ.get("INGEST_KEY")
    return bool(expected and candidate and hmac.compare_digest(expected, candidate))
