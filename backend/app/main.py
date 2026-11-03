import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from . import api, auth, inference, security, storage
from .schemas import message_adapter


@asynccontextmanager
async def lifespan(_: FastAPI):
    inference.load_models()
    await storage.open_pool()
    admin, password = os.environ.get("ADMIN_USER"), os.environ.get("ADMIN_PASSWORD")
    if admin and password:
        await storage.ensure_user(admin, security.hash_password(password), "admin")
    yield
    await storage.close_pool()


app = FastAPI(title="Dip", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(api.router)


@app.get("/health")
def health():
    return {"status": "ok", "models": inference.models_loaded()}


@app.websocket("/ws/ingest")
async def ingest(ws: WebSocket, key: str | None = None):
    """Príjem dát zo simulátora. Vyžaduje ?key=INGEST_KEY, identifikátory sa pred uložením pseudonymizujú."""
    if not security.ingest_key_ok(key):
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = message_adapter.validate_json(raw)
            except ValidationError as e:
                await ws.send_json({"ok": False, "error": e.errors(include_url=False, include_context=False)})
                continue
            msg.session = security.pseudonymize(f"{msg.participant}/{msg.session}", "s")
            msg.participant = security.pseudonymize(msg.participant, "p")
            await storage.save(msg)
            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
