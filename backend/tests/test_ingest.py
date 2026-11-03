import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import security, storage
from app.main import app

SAMPLE = {
    "type": "sample", "participant": "P01", "session": "S1", "t": 1700000000000, "phase": 1,
    "heart_rate": 80,
    "head": {"pos": {"x": 0, "y": 1.7, "z": 0}, "rot": {"x": 0, "y": 0, "z": 0, "w": 1}},
}
URL = "/ws/ingest?key=test-ingest-key"


@pytest.fixture
def saved(monkeypatch):
    items = []

    async def fake_save(msg):
        items.append(msg)

    monkeypatch.setattr(storage, "save", fake_save)
    return items


def send(payload, url=URL):
    client = TestClient(app)
    with client.websocket_connect(url) as ws:
        ws.send_json(payload)
        return ws.receive_json()


def test_valid_sample_is_saved_with_pseudonyms(saved):
    assert send(SAMPLE) == {"ok": True}
    assert saved[0].participant == security.pseudonymize("P01", "p")
    assert saved[0].participant != "P01"
    assert "P01" not in saved[0].session


def test_same_participant_gets_same_pseudonym(saved):
    send(SAMPLE)
    send({**SAMPLE, "session": "S2"})
    assert saved[0].participant == saved[1].participant
    assert saved[0].session != saved[1].session


def test_valid_event_is_saved(saved):
    event = {"type": "event", "participant": "P01", "session": "S1", "t": 1, "phase": 2,
             "kind": "reaction_time", "value_ms": 350}
    assert send(event) == {"ok": True}


def test_heart_rate_out_of_range_is_rejected(saved):
    assert send({**SAMPLE, "heart_rate": 500})["ok"] is False
    assert saved == []


def test_unknown_type_is_rejected(saved):
    assert send({**SAMPLE, "type": "nieco"})["ok"] is False


@pytest.mark.parametrize("url", ["/ws/ingest", "/ws/ingest?key=zly"])
def test_missing_or_wrong_key_is_refused(saved, url):
    with pytest.raises(WebSocketDisconnect):
        send(SAMPLE, url)
    assert saved == []
