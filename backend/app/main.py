import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from . import api, auth, devices, inference, security, storage, users
from .schemas import message_adapter


logger = logging.getLogger("dip")


@asynccontextmanager
async def lifespan(_: FastAPI):
    inference.load_models()
    await storage.open_pool()
    admin, password = os.environ.get("ADMIN_USER"), os.environ.get("ADMIN_PASSWORD")
    if admin and password:
        await storage.ensure_user(admin, security.hash_password(password), "admin")
    yield
    await storage.close_pool()


# Opis rozhrania je len pre prihlásených, stránky /docs a /redoc sú vypnuté.
app = FastAPI(title="Dip", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(users.router)
app.include_router(users.me_router)
app.include_router(devices.router)


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(auth.current_user)])
def openapi_spec():
    return app.openapi()


@app.get("/health")
def health():
    return {"status": "ok", "models": inference.models_loaded()}


@app.websocket("/ws/ingest")
async def ingest(ws: WebSocket, key: str | None = None):
    """Príjem dát zo simulátora, identifikátory sa pred uložením pseudonymizujú.

    Headset člena pošle ako prvú správu {"type": "auth", "token": "..."} a jeho dáta patria vlastníkovi tokenu.
    Spoločný kľúč ?key=INGEST_KEY ostáva pre mock sender a meranie, účastníka vtedy určuje správa.
    """
    device = None
    if key is not None:
        if not security.ingest_key_ok(key):
            await ws.close(code=1008)
            return
        await ws.accept()
    else:
        await ws.accept()
        try:
            device = await devices.authenticate(ws)
        except WebSocketDisconnect:
            return
        if device is None:
            await ws.close(code=1008)
            return
        await ws.send_json({"ok": True})
        devices.connections.setdefault(device["id"], set()).add(ws)
        await storage.touch_device(device["id"])
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = message_adapter.validate_json(raw)
            except ValidationError as e:
                await ws.send_json({"ok": False, "error": e.errors(include_url=False, include_context=False, include_input=False)})
                continue
            # Pri headsete rozhoduje vlastník tokenu, meno v správe sa ignoruje.
            name = device["owner"] if device else msg.participant
            msg.session = security.pseudonymize(f"{name}/{msg.session}", "s")
            msg.participant = security.participant_code(name)
            try:
                await storage.save(msg)
            except Exception:
                logger.exception("Uloženie správy zlyhalo")
                await ws.send_json({"ok": False, "error": "Správu sa nepodarilo uložiť"})
                continue
            await ws.send_json({"ok": True})
    except (WebSocketDisconnect, RuntimeError):
        # RuntimeError: spojenie zavrelo odpojenie headsetu na webe.
        pass
    finally:
        if device:
            devices.connections.get(device["id"], set()).discard(ws)
            await storage.touch_device(device["id"])
