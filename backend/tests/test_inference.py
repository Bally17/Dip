import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import inference, storage
from app.main import app

IDENTITY = {"x": 0, "y": 0, "z": 0, "w": 1}


def rows(seconds=6, hz=10, hr=80.0):
    return [(i / hz, hr, IDENTITY) for i in range(int(seconds * hz))]


def test_identity_rotation_gives_zero_angles():
    assert inference.quat_to_pitch_yaw(IDENTITY) == (0, 0)


def test_yaw_rotation_is_recovered():
    half = math.radians(40) / 2
    _, yaw = inference.quat_to_pitch_yaw({"x": 0, "y": math.sin(half), "z": 0, "w": math.cos(half)})
    assert yaw == pytest.approx(40)


def test_window_is_resampled_to_25hz():
    w = inference.to_window(rows())
    assert len(w) == 125
    assert np.allclose(w["hr"], 80.0)


def test_too_short_session_gives_no_window():
    assert inference.to_window(rows(seconds=2)) is None


def test_missing_heart_rate_is_skipped():
    assert inference.to_window([(i / 10, None, IDENTITY) for i in range(60)]) is None


class FakeModel:
    def predict_proba(self, x):
        return np.array([[0.3, 0.7]])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(inference, "_bundle", {"model": FakeModel(), "features": list(inference.window_features(inference.to_window(rows())))})

    async def fake_recent(session, seconds):
        return rows() if session == "ok" else []

    monkeypatch.setattr(storage, "recent_samples", fake_recent)
    return TestClient(app)


def test_risk_endpoint_returns_probability(client):
    r = client.get("/sessions/ok/risk")
    assert r.status_code == 200
    assert r.json()["probability"] == pytest.approx(0.7)


def test_risk_endpoint_404_without_data(client):
    assert client.get("/sessions/none/risk").status_code == 404


def test_risk_endpoint_503_without_model(client, monkeypatch):
    monkeypatch.setattr(inference, "_bundle", None)
    assert client.get("/sessions/ok/risk").status_code == 503
