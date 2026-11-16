import pytest
from fastapi.testclient import TestClient

from app import auth, security, storage
from app.main import app
from app.security import LoginLimiter


def test_limiter_blocks_after_max_failures_and_frees_after_the_window():
    now = [1000.0]
    limiter = LoginLimiter(max_failures=3, window_s=60, clock=lambda: now[0])
    for _ in range(3):
        assert limiter.retry_after("admin") == 0
        limiter.failed("admin")
    assert limiter.retry_after("admin") == 60
    assert limiter.retry_after("ADMIN") == 60
    assert limiter.retry_after("iny") == 0
    now[0] += 61
    assert limiter.retry_after("admin") == 0


def test_limiter_forgets_failures_after_success():
    limiter = LoginLimiter(max_failures=2, window_s=60, clock=lambda: 0.0)
    limiter.failed("admin")
    limiter.succeeded("admin")
    limiter.failed("admin")
    assert limiter.retry_after("admin") == 0


@pytest.fixture
def client(monkeypatch):
    async def get_user(name):
        if name != "admin":
            return None
        return {"username": "admin", "role": "admin", "password_hash": security.hash_password("pw")}

    monkeypatch.setattr(storage, "get_user", get_user)
    monkeypatch.setattr(auth, "limiter", LoginLimiter(max_failures=3, window_s=60))
    return TestClient(app)


def login(client, password):
    return client.post("/auth/login", json={"username": "admin", "password": password})


def test_login_is_locked_after_repeated_wrong_passwords(client):
    for _ in range(3):
        assert login(client, "zle").status_code == 401
    locked = login(client, "pw")
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0


def test_successful_login_resets_the_counter(client):
    assert login(client, "zle").status_code == 401
    assert login(client, "zle").status_code == 401
    assert login(client, "pw").status_code == 200
    assert login(client, "zle").status_code == 401
    assert login(client, "pw").status_code == 200


def test_api_description_needs_a_token_and_the_docs_page_is_off(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 401
    token = login(client, "pw").json()["access_token"]
    spec = client.get("/openapi.json", headers={"Authorization": f"Bearer {token}"})
    assert spec.status_code == 200 and "/sessions" in spec.json()["paths"]
