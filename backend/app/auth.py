from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from pydantic import BaseModel

from . import security, storage

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)
limiter = security.LoginLimiter()


class Login(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(body: Login):
    wait = limiter.retry_after(body.username)
    if wait:
        raise HTTPException(429, "Priveľa nesprávnych pokusov, skús to neskôr", headers={"Retry-After": str(wait)})
    user = await storage.get_user(body.username)
    if not user or not security.verify_password(user["password_hash"], body.password):
        limiter.failed(body.username)
        raise HTTPException(401, "Nesprávne meno alebo heslo")
    limiter.succeeded(body.username)
    return {
        "access_token": security.create_token(user["username"], user["role"]),
        "token_type": "bearer",
        "role": user["role"],
    }


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if creds is None:
        raise HTTPException(401, "Chýba prihlásenie")
    try:
        claims = security.decode_token(creds.credentials)
    except PyJWTError:
        raise HTTPException(401, "Neplatný alebo expirovaný token")
    return {"username": claims["sub"], "role": claims["role"]}


def admin_only(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Vyžaduje sa rola admin")
    return user


def staff_only(user: dict = Depends(current_user)) -> dict:
    if user["role"] not in ("admin", "researcher"):
        raise HTTPException(403, "Vyžaduje sa rola admin alebo výskumník")
    return user


def own_participant(user: dict) -> str | None:
    """Pseudonym, na ktorý je člen obmedzený. None znamená bez obmedzenia (admin, výskumník)."""
    return security.participant_code(user["username"]) if user["role"] == "member" else None


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    """Prihlásený účet. Člen dostane aj pseudonym, pod ktorým sú jeho merania."""
    return {**user, "participant": own_participant(user)}
