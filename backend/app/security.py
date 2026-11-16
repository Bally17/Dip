"""Heslá, JWT tokeny a pseudonymizácia identifikátorov."""
import hashlib
import hmac
import math
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


def participant_code(username: str) -> str:
    """Pseudonym, pod ktorým sú merania člena. Rovnaký výpočet ako pri mene zo simulátora."""
    return pseudonymize(username, "p")


def ingest_key_ok(candidate: str | None) -> bool:
    expected = os.environ.get("INGEST_KEY")
    return bool(expected and candidate and hmac.compare_digest(expected, candidate))


class LoginLimiter:
    """Po max_failures nesprávnych heslách zamkne meno do konca okna od prvého pokusu.

    Počíta sa podľa mena, nie podľa adresy: za reverzným proxy majú všetci klienti rovnakú adresu.
    Stav je v pamäti jedného procesu, po reštarte servera sa vynuluje.
    """

    def __init__(self, max_failures: int = 5, window_s: float = 15 * 60, clock=time.monotonic):
        self.max_failures, self.window_s, self._clock = max_failures, window_s, clock
        self._failures: dict[str, list[float]] = {}

    def _recent(self, username: str) -> list[float]:
        key, now = username.lower(), self._clock()
        recent = [t for t in self._failures.get(key, []) if now - t < self.window_s]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def retry_after(self, username: str) -> int:
        """Sekundy do odomknutia, 0 ak sa dá prihlásiť."""
        recent = self._recent(username)
        if len(recent) < self.max_failures:
            return 0
        return max(1, math.ceil(recent[0] + self.window_s - self._clock()))

    def failed(self, username: str) -> None:
        if len(self._failures) > 10_000:  # poistka proti zaplneniu pamäte vymyslenými menami
            self._failures.clear()
        self._failures.setdefault(username.lower(), []).append(self._clock())

    def succeeded(self, username: str) -> None:
        self._failures.pop(username.lower(), None)
