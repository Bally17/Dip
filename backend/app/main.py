from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from . import storage
from .schemas import message_adapter


@asynccontextmanager
async def lifespan(_: FastAPI):
    await storage.open_pool()
    yield
    await storage.close_pool()


app = FastAPI(title="Dip", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/ingest")
async def ingest(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = message_adapter.validate_json(raw)
            except ValidationError as e:
                await ws.send_json({"ok": False, "error": e.errors(include_url=False, include_context=False)})
                continue
            await storage.save(msg)
            await ws.send_json({"ok": True})
    except WebSocketDisconnect:
        pass
