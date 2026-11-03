import math

import numpy as np
import pytest

from app import inference

IDENTITY = {"x": 0, "y": 0, "z": 0, "w": 1}


def rows(seconds=6, hz=10, hr=80.0):
    return [{"t": i / hz, "phase": 0, "hr": hr, "head": {"rot": IDENTITY}} for i in range(int(seconds * hz))]


def test_identity_rotation_gives_zero_angles():
    assert inference.quat_to_pitch_yaw(IDENTITY) == (0, 0)


def test_yaw_rotation_is_recovered():
    half = math.radians(40) / 2
    _, yaw = inference.quat_to_pitch_yaw({"x": 0, "y": math.sin(half), "z": 0, "w": math.cos(half)})
    assert yaw == pytest.approx(40)


def test_window_is_resampled_to_25hz():
    w = inference.to_window(rows())
    assert len(w) == 126
    assert np.allclose(w["hr"], 80.0)


def test_too_short_session_gives_no_window():
    assert inference.to_window(rows(seconds=2)) is None


def test_missing_heart_rate_is_skipped():
    no_hr = [{**r, "hr": None} for r in rows()]
    assert inference.to_window(no_hr) is None


def test_models_are_loaded_from_directory(tmp_path, monkeypatch):
    import joblib
    bundle = {"model": object(), "features": []}
    joblib.dump(bundle, tmp_path / "model.joblib")
    joblib.dump(bundle, tmp_path / "model_fear.joblib")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    inference.load_models()
    assert sorted(inference.models_loaded()) == ["arousal", "fear"]
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "prazdny"))
    inference.load_models()
    assert inference.models_loaded() == []
