import pytest
from fastapi.testclient import TestClient

from app import devices, security, storage
from app.main import app

PASSWORD = "dlhe-heslo-1"
JANA = security.participant_code("jana")


@pytest.fixture
def client(monkeypatch):
    users = {"admin": "admin", "viewer": "researcher", "jana": "member"}
    password_hash = security.hash_password(PASSWORD)
    erased, revoked = [], []

    async def get_user(name):
        return {"username": name, "role": users[name], "password_hash": password_hash} if name in users else None

    async def list_users():
        return [{"username": name, "role": role} for name, role in users.items()]

    async def delete_user(username):
        return users.pop(username, None) is not None

    async def delete_participant(code):
        erased.append(code)
        return code == JANA

    async def list_devices(owner):
        return [{"id": "d1", "paired_at": 1.0, "last_seen": None}] if owner == "jana" else []

    async def revoke_device(device_id, owner):
        revoked.append(device_id)
        return True

    async def list_participants():
        return [{"code": JANA, "sessions": 1}]

    async def list_sessions(participant=None):
        return [{"id": "s_1", "participant": JANA, "samples": 10}]

    async def session_exists(session):
        return True

    async def session_samples(session, since=None, limit=100000):
        return []

    async def session_events(session):
        return {"events": []}

    for fn in (get_user, list_users, delete_user, delete_participant, list_devices, revoke_device,
               list_participants, list_sessions, session_exists, session_samples, session_events):
        monkeypatch.setattr(storage, fn.__name__, fn, raising=False)
    devices.connections.clear()
    c = TestClient(app)
    c.users, c.erased, c.revoked = users, erased, revoked
    return c


def auth(client, user="jana"):
    token = client.post("/auth/login", json={"username": user, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_member_erases_own_measurements_and_keeps_the_account(client):
    assert client.delete("/me/data", headers=auth(client)).json() == {"erased": True}
    assert client.erased == [JANA]
    assert "jana" in client.users


def test_member_deletes_account_with_data_and_headsets(client):
    assert client.delete("/me", headers=auth(client)).json() == {"deleted": True}
    assert client.erased == [JANA] and client.revoked == ["d1"]
    assert "jana" not in client.users


@pytest.mark.parametrize("path", ["/me", "/me/data"])
def test_self_erasure_is_for_members_only(client, path):
    assert client.delete(path).status_code == 401
    for user in ("admin", "viewer"):
        assert client.delete(path, headers=auth(client, user)).status_code == 403
    assert client.erased == [] and len(client.users) == 3


@pytest.mark.parametrize("path", ["/users", "/participants", "/sessions", "/sessions/s_1/export?format=json", "/auth/me"])
def test_admin_never_receives_a_member_name(client, path):
    response = client.get(path, headers=auth(client, "admin"))
    assert response.status_code == 200
    assert "jana" not in response.text


def test_member_sees_own_pseudonym(client):
    assert client.get("/auth/me", headers=auth(client)).json() == {"username": "jana", "role": "member", "participant": JANA}
    assert client.get("/auth/me", headers=auth(client, "admin")).json() == {"username": "admin", "role": "admin", "participant": None}
