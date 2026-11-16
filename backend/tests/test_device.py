from app import device, storage

from test_api import auth, client  # noqa: F401


def stream(seconds=10, hz=25, delay=0.02, start=1000.0):
    return [{"t": start + i / hz, "received": start + i / hz + delay} for i in range(int(seconds * hz))]


def test_rate_is_the_real_sampling_frequency():
    assert device.stats(stream(hz=25), now=1010.0)["rate_hz"] == 25.0
    assert device.stats(stream(hz=10), now=1010.0)["rate_hz"] == 10.0


def test_gap_is_counted_and_its_length_reported():
    rows = stream(seconds=4) + stream(seconds=4, start=1006.0)
    out = device.stats(rows, now=1010.0)
    assert out["gaps"] == 1
    assert round(out["longest_gap_s"], 1) == 2.0
    assert device.stats(stream(), now=1010.0)["gaps"] == 0


def test_delay_is_time_between_sample_and_its_arrival():
    rows = stream(delay=0.02)
    rows[-1]["received"] = rows[-1]["t"] + 1.5
    out = device.stats(rows, now=1012.0)
    assert round(out["delay_ms"]) == 20
    assert round(out["delay_max_ms"]) == 1500


def test_rows_without_arrival_time_give_no_delay():
    rows = [{"t": r["t"], "received": None} for r in stream()]
    out = device.stats(rows, now=1010.0)
    assert out["delay_ms"] is None and out["delay_max_ms"] is None
    assert out["last_message_age_s"] is None and out["connected"] is False
    assert out["rate_hz"] == 25.0


def test_connection_state_follows_the_last_message():
    rows = stream()
    last = rows[-1]["received"]
    assert device.stats(rows, now=last + 1)["connected"] is True
    late = device.stats(rows, now=last + 30)
    assert late["connected"] is False
    assert round(late["last_message_age_s"]) == 30


def test_empty_session_has_no_values():
    assert device.stats([], now=1.0) == {
        "samples": 0, "rate_hz": None, "gaps": 0, "longest_gap_s": None, "delay_ms": None,
        "delay_max_ms": None, "last_message_age_s": None, "connected": False,
    }


def test_device_endpoint_returns_stats(client, monkeypatch):  # noqa: F811
    async def arrival_times(session):
        return stream()

    monkeypatch.setattr(storage, "arrival_times", arrival_times)
    assert client.get("/sessions/s_ok/device").status_code == 401
    body = client.get("/sessions/s_ok/device", headers=auth(client)).json()
    assert body["session"] == "s_ok"
    assert body["rate_hz"] == 25.0 and body["samples"] == 250
    assert client.get("/sessions/nic/device", headers=auth(client)).status_code == 404
