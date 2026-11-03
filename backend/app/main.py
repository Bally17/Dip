from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from . import inference, storage
from .features import WINDOW_S
from .schemas import message_adapter


@asynccontextmanager
async def lifespan(_: FastAPI):
    inference.load_model()
    await storage.open_pool()
    yield
    await storage.close_pool()


app = FastAPI(title="Dip", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": inference.model_loaded()}


@app.get("/sessions/{session}/risk")
async def session_risk(session: str):
    if not inference.model_loaded():
        raise HTTPException(503, "Model nie je načítaný")
    window = inference.to_window(await storage.recent_samples(session, WINDOW_S + 1))
    if window is None:
        raise HTTPException(404, "Relácia nemá dosť dát na odhad")
    return {"session": session, "window_s": WINDOW_S, "probability": inference.risk(window)}


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
