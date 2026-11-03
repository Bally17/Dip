"""Odhad pravdepodobnosti vysokého arousalu z posledných sekúnd relácie."""
import math
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .features import HZ, WINDOW_S, window_features

MIN_SPAN_S = WINDOW_S - 1

_bundle = None


def load_model() -> None:
    global _bundle
    path = Path(os.environ.get("MODEL_PATH", "/models/model.joblib"))
    _bundle = joblib.load(path) if path.exists() else None


def model_loaded() -> bool:
    return _bundle is not None


def quat_to_pitch_yaw(rot: dict) -> tuple[float, float]:
    """Uhly v stupňoch z kvaterniónu (os Y = yaw, os X = pitch)."""
    x, y, z, w = rot["x"], rot["y"], rot["z"], rot["w"]
    yaw = math.atan2(2 * (w * y + x * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * x - y * z))))
    return math.degrees(pitch), math.degrees(yaw)


def to_window(rows: list[tuple[float, float | None, dict]]) -> pd.DataFrame | None:
    """Riadky (čas v s, tep, rotácia hlavy) prevedie na okno 25 Hz. Vráti None, ak je dát málo."""
    rows = [r for r in rows if r[1] is not None]
    if len(rows) < 2:
        return None
    t = np.array([r[0] for r in rows])
    if t[-1] - t[0] < MIN_SPAN_S:
        return None
    pitch, yaw = np.array([quat_to_pitch_yaw(r[2]) for r in rows]).T
    grid = np.arange(t[-1] - WINDOW_S, t[-1], 1 / HZ)
    grid = grid[grid >= t[0]]
    return pd.DataFrame({
        "pitch": np.interp(grid, t, pitch),
        "yaw": np.degrees(np.interp(grid, t, np.unwrap(np.radians(yaw)))),
        "hr": np.interp(grid, t, [r[1] for r in rows]),
    })


def risk(window: pd.DataFrame) -> float:
    feats = window_features(window)
    x = np.array([[feats[name] for name in _bundle["features"]]])
    return float(_bundle["model"].predict_proba(x)[0, 1])
