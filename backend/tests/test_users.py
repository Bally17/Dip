import pytest
from fastapi.testclient import TestClient

from app import security, storage
from app.main import app

PASSWORD = "dlhe-heslo-1"
JANA = security.pseudonymize("jana", "p")


@pytest.fixture
def client(monkeypatch):
    users = {"admin": "admin", "viewer": "researcher", "jana": "member"}
    password_hash = security.hash_password(PASSWORD)
    sessions = {"s_jana": JANA, "s_cudzia": "p_niekto_iny"}

    async def get_user(name):
        return {"username": name, "role": users[name], "password_hash": password_hash} if name in users else None

    async def create_user(username, password_hash, role):
        if username in users:
            return False
        users[username] = role
        return True

    async def list_users():
        return [{"username": name, "role": role} for name, role in users.items()]

    async def delete_user(username):
        return users.pop(username, None) is not None

    async def session_exists(session):
        return session in sessions

    async def session_participant(session):
        return sessions.get(session)

    async def list_sessions(participant=None):
        return [{"id": s, "participant": p} for s, p in sessions.items() if participant in (None, p)]

    async def list_participants():
        return [{"code": p} for p in sessions.values()]

    async def session_samples(session, since=None, limit=100000):
        return []

    async def session_events(session):
        return {"events": []}

    async def session_summary(session):
        return {}

    async def arrival_times(session):
        return []

    for fn in (get_user, create_user, list_users, delete_user, session_exists, session_participant, list_sessions,
               list_participants, session_samples, session_events, session_summary, arrival_times):
        monkeypatch.setattr(storage, fn.__name__, fn, raising=False)
    c = TestClient(app)
    c.users = users
    return c


def auth(client, user="admin"):
    token = client.post("/auth/login", json={"username": user, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_creates_member_who_can_log_in(client):
    r = client.post("/users", json={"username": "peter", "password": PASSWORD, "role": "member"}, headers=auth(client))
    assert r.status_code == 201
    assert r.json() == {"id": security.pseudonymize("peter", "p"), "name": security.pseudonymize("peter", "p"), "role": "member"}
    login = client.post("/auth/login", json={"username": "peter", "password": PASSWORD}).json()
    assert login["role"] == "member"


def test_create_user_checks_input_and_duplicates(client):
    h = auth(client)
    assert client.post("/users", json={"username": "peter", "password": "kratke", "role": "member"}, headers=h).status_code == 422
    assert client.post("/users", json={"username": "peter", "password": PASSWORD, "role": "boss"}, headers=h).status_code == 422
    assert client.post("/users", json={"username": "p", "password": PASSWORD, "role": "member"}, headers=h).status_code == 422
    assert client.post("/users", json={"username": "jana", "password": PASSWORD, "role": "member"}, headers=h).status_code == 409


def test_only_admin_manages_users(client):
    body = {"username": "peter", "password": PASSWORD, "role": "member"}
    for user in ("viewer", "jana"):
        h = auth(client, user)
        assert client.post("/users", json=body, headers=h).status_code == 403
        assert client.get("/users", headers=h).status_code == 403
        assert client.delete(f"/users/{JANA}", headers=h).status_code == 403
    assert "peter" not in client.users and "jana" in client.users


def test_user_list_shows_member_by_pseudonym_only(client):
    r = client.get("/users", headers=auth(client))
    by_id = {u["id"]: u for u in r.json()}
    assert by_id[JANA] == {"id": JANA, "name": JANA, "role": "member"}
    assert by_id["viewer"] == {"id": "viewer", "name": "viewer", "role": "researcher"}
    assert "jana" not in r.text


def test_admin_deletes_user_but_not_self(client):
    h = auth(client)
    assert client.delete(f"/users/{JANA}", headers=h).json() == {"deleted": JANA}
    assert "jana" not in client.users
    assert client.delete(f"/users/{JANA}", headers=h).status_code == 404
    assert client.delete("/users/admin", headers=h).status_code == 400
    assert "admin" in client.users


def test_member_lists_only_own_sessions(client):
    assert [s["id"] for s in client.get("/sessions", headers=auth(client, "jana")).json()] == ["s_jana"]
    assert len(client.get("/sessions", headers=auth(client, "viewer")).json()) == 2
    assert len(client.get("/sessions", headers=auth(client)).json()) == 2


@pytest.mark.parametrize("path", ["samples", "summary", "device", "export", "risk", "risk/history"])
def test_member_cannot_open_foreign_session(client, path):
    h = auth(client, "jana")
    assert client.get(f"/sessions/s_cudzia/{path}", headers=h).status_code == 404


def test_member_opens_own_session_and_staff_any(client):
    assert client.get("/sessions/s_jana/samples", headers=auth(client, "jana")).status_code == 200
    assert client.get("/sessions/s_cudzia/samples", headers=auth(client, "viewer")).status_code == 200


def test_member_cannot_list_participants(client):
    assert client.get("/participants", headers=auth(client, "jana")).status_code == 403
    assert client.get("/participants", headers=auth(client, "viewer")).status_code == 200
