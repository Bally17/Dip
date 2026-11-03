"""REST rozhranie pre frontend: účastníci, relácie, história, odhady, export."""
import csv
import json
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from . import inference, storage
from .auth import admin_only, current_user
from .features import WINDOW_S

router = APIRouter(dependencies=[Depends(current_user)])


def _point(row: dict) -> dict:
    pitch, yaw = inference.quat_to_pitch_yaw(row["head"]["rot"])
    return {"t": row["t"], "phase": row["phase"], "hr": row["hr"], "pitch": pitch, "yaw": yaw}


async def _require_session(session: str) -> None:
    if not await storage.session_exists(session):
        raise HTTPException(404, "Relácia neexistuje")


@router.get("/participants")
async def participants():
    return await storage.list_participants()


@router.get("/sessions")
async def sessions(participant: str | None = None):
    return await storage.list_sessions(participant)


@router.get("/sessions/{session}/summary")
async def summary(session: str):
    await _require_session(session)
    return {"session": session, **await storage.session_summary(session), **await storage.session_events(session)}


@router.get("/sessions/{session}/samples")
async def samples(session: str, since: float | None = None, max_points: int = Query(2000, ge=10, le=20000)):
    """Vzorky relácie. `since` (Unix čas v s) vráti len novšie, vhodné na živé zobrazenie."""
    await _require_session(session)
    rows = await storage.session_samples(session, since)
    stride = max(1, len(rows) // max_points)
    return [_point(r) for r in rows[::stride]]


@router.get("/sessions/{session}/risk")
async def risk(session: str):
    if not inference.models_loaded():
        raise HTTPException(503, "Modely nie sú načítané")
    window = inference.to_window(await storage.recent_samples(session, WINDOW_S + 1))
    if window is None:
        raise HTTPException(404, "Relácia nemá dosť dát na odhad")
    return {"session": session, "window_s": WINDOW_S, "probabilities": inference.risks(window)}


@router.get("/sessions/{session}/risk/history")
async def risk_history(session: str, step: float = Query(2.5, ge=0.5, le=30)):
    if not inference.models_loaded():
        raise HTTPException(503, "Modely nie sú načítané")
    await _require_session(session)
    return inference.risk_series(await storage.session_samples(session), step)


@router.get("/sessions/{session}/export")
async def export(session: str, format: str = Query("csv", pattern="^(csv|json)$")):
    await _require_session(session)
    points = [_point(r) | {"head_x": r["head"]["pos"]["x"], "head_y": r["head"]["pos"]["y"],
                           "head_z": r["head"]["pos"]["z"]} for r in await storage.session_samples(session)]
    name = f"attachment; filename={session}.{format}"
    if format == "json":
        body = {"session": session, "samples": points, **await storage.session_events(session)}
        return Response(json.dumps(body), media_type="application/json",
                        headers={"Content-Disposition": name})
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["t", "phase", "hr", "pitch", "yaw", "head_x", "head_y", "head_z"])
    writer.writeheader()
    writer.writerows(points)
    return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": name})


@router.delete("/participants/{code}", dependencies=[Depends(admin_only)])
async def erase_participant(code: str):
    """Právo na vymazanie (GDPR): zmaže účastníka aj všetky jeho relácie a dáta."""
    if not await storage.delete_participant(code):
        raise HTTPException(404, "Účastník neexistuje")
    return {"deleted": code}
