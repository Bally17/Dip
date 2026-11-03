"""Odhad stavu účastníka (arousal, strach) z tepu a pohybu hlavy."""
import math
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .features import HZ, STEP_S, WINDOW_S, window_features

MIN_SPAN_S = WINDOW_S - 1
MODEL_NAMES = ("arousal", "fear")

_bundles: dict[str, dict] = {}


def load_models() -> None:
    """Načíta model_<názov>.joblib z MODEL_DIR. Starší model.joblib berie ako arousal."""
    _bundles.clear()
    folder = Path(os.environ.get("MODEL_DIR", "/models"))
    for name in MODEL_NAMES:
        path = folder / f"model_{name}.joblib"
        if not path.exists() and name == "arousal":
            path = folder / "model.joblib"
        if path.exists():
            _bundles[name] = joblib.load(path)


def models_loaded() -> list[str]:
    return list(_bundles)


def quat_to_pitch_yaw(rot: dict) -> tuple[float, float]:
    """Uhly v stupňoch z kvaterniónu (os Y = yaw, os X = pitch)."""
    x, y, z, w = rot["x"], rot["y"], rot["z"], rot["w"]
    yaw = math.atan2(2 * (w * y + x * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * x - y * z))))
    return math.degrees(pitch), math.degrees(yaw)


def angles(rows: list[dict]) -> list[tuple[float, float]]:
    return [quat_to_pitch_yaw(r["head"]["rot"]) for r in rows]


def resample(rows: list[dict]) -> pd.DataFrame | None:
    """Vzorky (t, hr, head) na rovnomernú os 25 Hz. None, ak je dát málo."""
    rows = [r for r in rows if r["hr"] is not None]
    if len(rows) < 2:
        return None
    t = np.array([r["t"] for r in rows])
    if t[-1] - t[0] < MIN_SPAN_S:
        return None
    pitch, yaw = np.array(angles(rows)).T
    grid = np.arange(t[0], t[-1], 1 / HZ)
    return pd.DataFrame({
        "t": grid,
        "pitch": np.interp(grid, t, pitch),
        "yaw": np.degrees(np.interp(grid, t, np.unwrap(np.radians(yaw)))),
        "hr": np.interp(grid, t, [r["hr"] for r in rows]),
    })


def to_window(rows: list[dict]) -> pd.DataFrame | None:
    """Posledných WINDOW_S sekúnd ako okno pre model."""
    full = resample(rows)
    if full is None:
        return None
    return full[full["t"] >= full["t"].iloc[-1] - WINDOW_S].reset_index(drop=True)


def risks(window: pd.DataFrame) -> dict[str, float]:
    feats = window_features(window)
    out = {}
    for name, bundle in _bundles.items():
        x = np.array([[feats[f] for f in bundle["features"]]])
        out[name] = float(bundle["model"].predict_proba(x)[0, 1])
    return out


def risk_series(rows: list[dict], step_s: float = STEP_S) -> list[dict]:
    """Odhady v posuvných oknách cez celú reláciu: [{t, arousal, fear}, ...]."""
    full = resample(rows)
    if full is None:
        return []
    win, step = int(WINDOW_S * HZ), max(1, int(step_s * HZ))
    series = []
    for start in range(0, len(full) - win + 1, step):
        w = full.iloc[start:start + win].reset_index(drop=True)
        series.append({"t": float(w["t"].iloc[-1]), **risks(w)})
    return series
