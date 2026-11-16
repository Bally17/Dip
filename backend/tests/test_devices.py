import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import devices, security, storage
from app.main import app

PASSWORD = "dlhe-heslo-1"
SAMPLE = {
    "type": "sample", "participant": "CUDZIE-MENO", "session": "S1", "t": 1700000000000, "phase": 1,
    "heart_rate": 80,
    "head": {"pos": {"x": 0, "y": 1.7, "z": 0}, "rot": {"x": 0, "y": 0, "z": 0, "w": 1}},
}


@pytest.fixture
def client(monkeypatch):
    users = {"admin": "admin", "jana": "member", "peter": "member"}
    password_hash = security.hash_password(PASSWORD)
    codes, registry, saved = {}, {}, []

    async def get_user(name):
        return {"username": name, "role": users[name], "password_hash": password_hash} if name in users else None

    async def save_pairing_code(code_hash, owner, expires_at):
        for key in [k for k, c in codes.items() if c["owner"] == owner]:
            del codes[key]
        codes[code_hash] = {"owner": owner, "expires_at": expires_at, "used": False}

    async def use_pairing_code(code_hash, now):
        code = codes.get(code_hash)
        if not code or code["used"] or code["expires_at"] <= now:
            return None
        code["used"] = True
        return code["owner"]

    async def create_device(owner, token_hash):
        device_id = f"d{len(registry) + 1}"
        registry[device_id] = {"id": device_id, "owner": owner, "token_hash": token_hash, "revoked": False,
                               "paired_at": 1000.0, "last_seen": None}
        return device_id

    async def device_by_token(token_hash):
        return next((d for d in registry.values() if d["token_hash"] == token_hash and not d["revoked"]), None)

    async def list_devices(owner):
        return [{"id": d["id"], "paired_at": d["paired_at"], "last_seen": d["last_seen"]}
                for d in registry.values() if d["owner"] == owner and not d["revoked"]]

    async def revoke_device(device_id, owner):
        device = registry.get(device_id)
        if not device or device["owner"] != owner or device["revoked"]:
            return False
        device["revoked"] = True
        return True

    async def touch_device(device_id):
        registry[device_id]["last_seen"] = 2000.0

    async def save(msg):
        saved.append(msg)

    for fn in (get_user, save_pairing_code, use_pairing_code, create_device, device_by_token, list_devices,
               revoke_device, touch_device, save):
        monkeypatch.setattr(storage, fn.__name__, fn, raising=False)
    monkeypatch.setattr(devices, "pair_limiter", security.LoginLimiter(max_failures=20))
    devices.connections.clear()
    c = TestClient(app)
    c.saved, c.registry = saved, registry
    return c


def auth(client, user="jana"):
    token = client.post("/auth/login", json={"username": user, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def pair(client, user="jana"):
    code = client.post("/devices/pairing-code", headers=auth(client, user)).json()["code"]
    return client.post("/devices/pair", json={"code": code}).json()


def test_member_gets_a_short_pairing_code(client):
    body = client.post("/devices/pairing-code", headers=auth(client)).json()
    assert len(body["code"]) == 6 and set(body["code"]) <= set(devices.ALPHABET)
    assert body["expires_in_s"] == 600


def test_only_member_can_ask_for_a_code(client):
    assert client.post("/devices/pairing-code").status_code == 401
    assert client.post("/devices/pairing-code", headers=auth(client, "admin")).status_code == 403


def test_code_is_exchanged_for_a_token_once(client):
    code = client.post("/devices/pairing-code", headers=auth(client)).json()["code"]
    first = client.post("/devices/pair", json={"code": code})
    assert first.status_code == 200 and len(first.json()["token"]) >= 40
    assert client.post("/devices/pair", json={"code": code}).status_code == 400
    assert client.post("/devices/pair", json={"code": "ZZZZZZ"}).status_code == 400


def test_code_is_accepted_in_lowercase_with_separators(client):
    code = client.post("/devices/pairing-code", headers=auth(client)).json()["code"]
    typed = f" {code[:3].lower()}-{code[3:].lower()} "
    assert client.post("/devices/pair", json={"code": typed}).status_code == 200


def test_expired_code_is_refused(client, monkeypatch):
    code = client.post("/devices/pairing-code", headers=auth(client)).json()["code"]
    real = devices.time.time
    monkeypatch.setattr(devices.time, "time", lambda: real() + 601)
    assert client.post("/devices/pair", json={"code": code}).status_code == 400


def test_new_code_cancels_the_previous_one(client):
    h = auth(client)
    old = client.post("/devices/pairing-code", headers=h).json()["code"]
    new = client.post("/devices/pairing-code", headers=h).json()["code"]
    assert client.post("/devices/pair", json={"code": old}).status_code == 400
    assert client.post("/devices/pair", json={"code": new}).status_code == 200


def test_guessing_codes_gets_locked(client):
    for _ in range(20):
        assert client.post("/devices/pair", json={"code": "ZZZZZZ"}).status_code == 400
    assert client.post("/devices/pair", json={"code": "ZZZZZZ"}).status_code == 429


def test_headset_token_is_stored_only_as_a_hash(client):
    token = pair(client)["token"]
    assert token not in str(client.registry)


def test_data_sent_with_a_token_belongs_to_its_owner(client):
    token = pair(client)["token"]
    with client.websocket_connect("/ws/ingest") as ws:
        ws.send_json({"type": "auth", "token": token})
        assert ws.receive_json() == {"ok": True}
        ws.send_json(SAMPLE)
        assert ws.receive_json() == {"ok": True}
        without_name = {k: v for k, v in SAMPLE.items() if k != "participant"}
        ws.send_json(without_name)
        assert ws.receive_json() == {"ok": True}
    assert [m.participant for m in client.saved] == [security.participant_code("jana")] * 2
    assert client.saved[0].session == client.saved[1].session
    assert "S1" not in client.saved[0].session and "jana" not in client.saved[0].session


@pytest.mark.parametrize("first", [{"type": "auth", "token": "vymysleny"}, {"type": "auth"}, SAMPLE])
def test_connection_without_a_valid_token_is_closed(client, first):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/ingest") as ws:
            ws.send_json(first)
            ws.receive_json()
            ws.send_json(SAMPLE)
            ws.receive_json()
    assert client.saved == []


def test_member_sees_own_headsets_and_whether_they_are_connected(client):
    token = pair(client)["token"]
    pair(client, "peter")
    h = auth(client)
    listed = client.get("/devices", headers=h).json()
    assert [d["id"] for d in listed] == ["d1"] and listed[0]["connected"] is False
    with client.websocket_connect("/ws/ingest") as ws:
        ws.send_json({"type": "auth", "token": token})
        ws.receive_json()
        assert client.get("/devices", headers=h).json()[0]["connected"] is True
    after = client.get("/devices", headers=h).json()[0]
    assert after["connected"] is False and after["last_seen"] == 2000.0


def test_disconnected_headset_cannot_send_any_more(client):
    token = pair(client)["token"]
    h = auth(client)
    assert client.delete("/devices/d1", headers=auth(client, "peter")).status_code == 404
    assert client.delete("/devices/d1", headers=h).json() == {"deleted": "d1"}
    assert client.get("/devices", headers=h).json() == []
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/ingest") as ws:
            ws.send_json({"type": "auth", "token": token})
            ws.receive_json()
            ws.send_json(SAMPLE)
            ws.receive_json()
    assert client.saved == []


def test_disconnecting_closes_an_open_connection(client):
    token = pair(client)["token"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/ingest") as ws:
            ws.send_json({"type": "auth", "token": token})
            ws.receive_json()
            client.delete("/devices/d1", headers=auth(client))
            ws.send_json(SAMPLE)
            ws.receive_json()
            ws.receive_json()
