import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import inference, security, storage
from app.main import app

IDENTITY = {"x": 0, "y": 0, "z": 0, "w": 1}


def rows(seconds=12, hz=10, hr=80.0):
    return [{"t": 1000 + i / hz, "phase": 0, "hr": hr,
             "head": {"pos": {"x": 0, "y": 1.7, "z": 0}, "rot": IDENTITY}} for i in range(int(seconds * hz))]


class FakeModel:
    def predict_proba(self, x):
        return np.array([[0.3, 0.7]])


@pytest.fixture
def client(monkeypatch):
    feats = list(inference.window_features(inference.to_window(rows())))
    monkeypatch.setattr(inference, "_bundles", {n: {"model": FakeModel(), "features": feats} for n in ("arousal", "fear")})
    data = rows()

    async def session_exists(s):
        return s == "s_ok"

    async def session_samples(s, since=None, limit=100000):
        return [r for r in data if since is None or r["t"] > since]

    async def recent_samples(s, seconds):
        return data if s == "s_ok" else []

    async def session_events(s):
        return {"events": [{"t": 1001.0, "phase": 0, "kind": "reaction_time", "value_ms": 400}], "questionnaires": []}

    async def get_user(name):
        users = {"admin": ("admin", "pw"), "viewer": ("researcher", "pw")}
        if name not in users:
            return None
        return {"username": name, "role": users[name][0], "password_hash": security.hash_password("pw")}

    deleted = []

    async def delete_participant(code):
        deleted.append(code)
        return code == "p_x"

    for fn in (session_exists, session_samples, recent_samples, session_events, get_user, delete_participant):
        monkeypatch.setattr(storage, fn.__name__, fn)
    c = TestClient(app)
    c.deleted = deleted
    return c


def auth(client, user="admin", password="pw"):
    r = client.post("/auth/login", json={"username": user, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"} if r.status_code == 200 else None


def test_login_wrong_password_is_401(client):
    assert client.post("/auth/login", json={"username": "admin", "password": "zle"}).status_code == 401
    assert client.post("/auth/login", json={"username": "neznamy", "password": "pw"}).status_code == 401


def test_endpoints_need_a_token(client):
    for path in ("/participants", "/sessions", "/sessions/s_ok/samples", "/sessions/s_ok/risk", "/auth/me"):
        assert client.get(path).status_code == 401, path
    assert client.get("/sessions", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_me_returns_role(client):
    assert client.get("/auth/me", headers=auth(client, "viewer")).json() == {"username": "viewer", "role": "researcher"}


def test_samples_have_angles_and_support_since(client):
    h = auth(client)
    all_points = client.get("/sessions/s_ok/samples", headers=h).json()
    assert {"t", "hr", "pitch", "yaw", "phase"} <= set(all_points[0])
    newer = client.get("/sessions/s_ok/samples", params={"since": all_points[-3]["t"]}, headers=h).json()
    assert len(newer) == 2


def test_samples_are_downsampled(client):
    points = client.get("/sessions/s_ok/samples", params={"max_points": 10}, headers=auth(client)).json()
    assert len(points) <= 20


def test_unknown_session_is_404(client):
    assert client.get("/sessions/zle/samples", headers=auth(client)).status_code == 404


def test_risk_returns_both_probabilities(client):
    body = client.get("/sessions/s_ok/risk", headers=auth(client)).json()
    assert body["probabilities"] == {"arousal": pytest.approx(0.7), "fear": pytest.approx(0.7)}


def test_risk_without_data_is_404_and_without_models_503(client, monkeypatch):
    assert client.get("/sessions/s_prazdna/risk", headers=auth(client)).status_code == 404
    monkeypatch.setattr(inference, "_bundles", {})
    assert client.get("/sessions/s_ok/risk", headers=auth(client)).status_code == 503


def test_risk_history_is_a_series(client):
    series = client.get("/sessions/s_ok/risk/history", headers=auth(client)).json()
    assert len(series) >= 3
    assert set(series[0]) == {"t", "arousal", "fear"}


def test_export_csv_and_json(client):
    h = auth(client)
    csv = client.get("/sessions/s_ok/export", headers=h)
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[0] == "t,phase,hr,pitch,yaw,head_x,head_y,head_z"
    assert len(csv.text.splitlines()) == 121
    js = client.get("/sessions/s_ok/export", params={"format": "json"}, headers=h).json()
    assert len(js["samples"]) == 120 and js["events"][0]["kind"] == "reaction_time"
    assert client.get("/sessions/s_ok/export", params={"format": "xml"}, headers=h).status_code == 422


def test_erasure_is_admin_only(client):
    assert client.delete("/participants/p_x", headers=auth(client, "viewer")).status_code == 403
    assert client.deleted == []
    assert client.delete("/participants/p_x", headers=auth(client)).json() == {"deleted": "p_x"}
    assert client.delete("/participants/p_zle", headers=auth(client)).status_code == 404
