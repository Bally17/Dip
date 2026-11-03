import asyncio

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import DeadlockDetected

from app import storage
from app.main import app

SAMPLE = {
    "type": "sample", "participant": "P01", "session": "S1", "t": 1700000000000, "phase": 1,
    "heart_rate": 80,
    "head": {"pos": {"x": 0, "y": 1.7, "z": 0}, "rot": {"x": 0, "y": 0, "z": 0, "w": 1}},
}


def test_deadlock_is_retried(monkeypatch):
    calls = []

    async def flaky(msg):
        calls.append(msg)
        if len(calls) < 3:
            raise DeadlockDetected("deadlock")

    monkeypatch.setattr(storage, "_save_once", flaky)
    asyncio.run(storage.save("sprava"))
    assert len(calls) == 3


def test_deadlock_gives_up_after_all_attempts(monkeypatch):
    async def always(msg):
        raise DeadlockDetected("deadlock")

    monkeypatch.setattr(storage, "_save_once", always)
    with pytest.raises(DeadlockDetected):
        asyncio.run(storage.save("sprava"))


def test_storage_failure_keeps_the_connection_alive(monkeypatch):
    async def broken(msg):
        raise RuntimeError("databáza nie je dostupná")

    monkeypatch.setattr(storage, "save", broken)
    with TestClient(app).websocket_connect("/ws/ingest?key=test-ingest-key") as ws:
        ws.send_json(SAMPLE)
        assert ws.receive_json()["ok"] is False
        ws.send_json(SAMPLE)
        assert ws.receive_json()["ok"] is False
