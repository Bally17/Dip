from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from pydantic import BaseModel

from . import security, storage

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


class Login(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(body: Login):
    user = await storage.get_user(body.username)
    if not user or not security.verify_password(user["password_hash"], body.password):
        raise HTTPException(401, "Nesprávne meno alebo heslo")
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


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return user
