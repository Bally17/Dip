"""Párovanie headsetu s účtom člena a overenie headsetu pri príjme dát.

Člen si na webe vypýta krátky kód, simulátor ho vymení za token a pod ním posiela dáta.
Kód aj token sa ukladajú len ako odtlačok (SHA-256).
"""
import asyncio
import hashlib
import json
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from pydantic import BaseModel, Field

from . import security, storage
from .auth import current_user

router = APIRouter()

# Bez znakov, ktoré sa pri prepisovaní z obrazovky pletú (0 a O, 1 a I).
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
CODE_TTL_S = 600
AUTH_TIMEOUT_S = 10

# Hádanie kódu: limit je spoločný pre všetkých, simulátor za proxy nemá vlastnú adresu.
pair_limiter = security.LoginLimiter(max_failures=20)
# Otvorené spojenia podľa headsetu, aby ich odpojenie na webe vedelo zavrieť. Platí pre jeden proces.
connections: dict[str, set[WebSocket]] = {}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def member_only(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "member":
        raise HTTPException(403, "Headset si páruje člen")
    return user


class PairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)


@router.post("/devices/pairing-code")
async def pairing_code(user: dict = Depends(member_only)):
    """Nový kód pre prihláseného člena. Predošlý nepoužitý kód tým prestane platiť."""
    code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
    await storage.save_pairing_code(digest(code), user["username"], time.time() + CODE_TTL_S)
    return {"code": code, "expires_in_s": CODE_TTL_S}


@router.post("/devices/pair")
async def pair(body: PairRequest):
    """Volá simulátor bez prihlásenia: vymení kód za token headsetu."""
    wait = pair_limiter.retry_after("pair")
    if wait:
        raise HTTPException(429, "Priveľa nesprávnych kódov, skús to neskôr", headers={"Retry-After": str(wait)})
    code = "".join(ch for ch in body.code.upper() if ch.isalnum())
    owner = await storage.use_pairing_code(digest(code), time.time())
    if owner is None:
        pair_limiter.failed("pair")
        raise HTTPException(400, "Kód je neplatný alebo už neplatí")
    token = secrets.token_urlsafe(32)
    return {"token": token, "device": await storage.create_device(owner, digest(token))}


@router.get("/devices")
async def my_devices(user: dict = Depends(member_only)):
    return [{**d, "connected": bool(connections.get(d["id"]))} for d in await storage.list_devices(user["username"])]


@router.delete("/devices/{device_id}")
async def disconnect(device_id: str, user: dict = Depends(member_only)):
    if not await storage.revoke_device(device_id, user["username"]):
        raise HTTPException(404, "Headset neexistuje")
    for ws in list(connections.get(device_id, ())):
        await ws.close(code=1008)
    return {"deleted": device_id}


async def authenticate(ws: WebSocket) -> dict | None:
    """Prvá správa spojenia musí byť {"type": "auth", "token": "..."}. Vráti headset alebo None."""
    try:
        first = json.loads(await asyncio.wait_for(ws.receive_text(), AUTH_TIMEOUT_S))
    except (asyncio.TimeoutError, ValueError):
        return None
    token = first.get("token") if isinstance(first, dict) and first.get("type") == "auth" else None
    if not isinstance(token, str):
        return None
    return await storage.device_by_token(digest(token))
