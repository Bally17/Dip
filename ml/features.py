"""Načítanie CEAP-360VR (Frame dáta, 25 Hz) a výpočet príznakov v oknách.

window_features() dostáva len stĺpce pitch, yaw, hr, aby fungovala aj na živých dátach z API.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HZ = 25
WINDOW_S = 5
STEP_S = 2.5

FEATURES = [
    "hr_mean", "hr_std", "hr_slope", "hr_range", "hr_delta",
    "head_speed_mean", "head_speed_std", "head_speed_max", "head_speed_median",
    "head_acc_mean", "head_speed_entropy",
    "head_pitch_mean", "head_pitch_std", "head_yaw_std",
    "head_still_frac",
]

STILL_DEG_S = 5.0
ENTROPY_BINS = np.array([0, 2, 5, 10, 20, 40, 80, np.inf])


def _load(root: Path, folder: str, pid: int, suffix: str, key: str) -> list:
    path = root / folder / "Frame" / f"P{pid}_{suffix}_FrameData.json"
    return json.loads(path.read_text())[key][0]


def load_participant(root: Path, pid: int) -> list[pd.DataFrame]:
    """Vráti jeden DataFrame na video: tep, pohyb hlavy, arousal a valence na spoločnej osi 25 Hz."""
    ann = _load(root, "3_AnnotationData", pid, "Annotation", "ContinuousAnnotation_FrameData")
    beh = _load(root, "4_BehaviorData", pid, "Behavior", "Behavior_FrameData")
    phy = _load(root, "5_PhysioData", pid, "Physio", "Physio_FrameData")
    videos = []
    for a, b, p in zip(
        ann["Video_Annotation_FrameData"],
        beh["Video_Behavior_FrameData"],
        phy["Video_Physio_FrameData"],
    ):
        hm = pd.DataFrame(b["HM"])
        hr = pd.DataFrame(p["HR_FrameData"])
        va = pd.DataFrame(a["TimeStamp_Valence_Arousal"])
        n = min(len(hm), len(hr), len(va))
        videos.append(pd.DataFrame({
            "t": hm["TimeStamp"].to_numpy()[:n],
            "pitch": hm["Pitch"].to_numpy()[:n],
            "yaw": hm["Yaw"].to_numpy()[:n],
            "hr": hr["HR"].to_numpy()[:n],
            "arousal": va["Arousal"].to_numpy()[:n],
            "valence": va["Valence"].to_numpy()[:n],
        }))
    return videos


def _entropy(speed: np.ndarray) -> float:
    counts = np.histogram(speed, bins=ENTROPY_BINS)[0]
    p = counts[counts > 0] / counts.sum()
    return float(-(p * np.log2(p)).sum())


def window_features(w: pd.DataFrame) -> dict:
    """Príznaky jedného okna. Uhlová rýchlosť hlavy v °/s, yaw sa zalamuje na ±180°."""
    dyaw = (np.diff(w["yaw"].to_numpy()) + 180) % 360 - 180
    dpitch = np.diff(w["pitch"].to_numpy())
    speed = np.hypot(dyaw, dpitch) * HZ
    acc = np.abs(np.diff(speed)) * HZ
    hr = w["hr"].to_numpy()
    x = np.arange(len(hr)) / HZ
    return {
        "hr_mean": hr.mean(),
        "hr_std": hr.std(),
        "hr_slope": np.polyfit(x, hr, 1)[0],
        "hr_range": hr.max() - hr.min(),
        "hr_delta": hr[-1] - hr[0],
        "head_speed_mean": speed.mean(),
        "head_speed_std": speed.std(),
        "head_speed_max": speed.max(),
        "head_speed_median": float(np.median(speed)),
        "head_acc_mean": acc.mean(),
        "head_speed_entropy": _entropy(speed),
        "head_pitch_mean": w["pitch"].mean(),
        "head_pitch_std": w["pitch"].std(),
        "head_yaw_std": np.std(np.unwrap(np.radians(w["yaw"])) * 180 / np.pi),
        "head_still_frac": float((speed < STILL_DEG_S).mean()),
    }


def build_dataset(root: Path, participants=range(1, 33)) -> pd.DataFrame:
    """Jeden riadok = jedno okno.

    label_arousal: arousal okna nad mediánom účastníka.
    label_fear: arousal nad mediánom a zároveň valence pod mediánom účastníka (proxy strachu).
    """
    win, step = int(WINDOW_S * HZ), int(STEP_S * HZ)
    rows = []
    for pid in participants:
        try:
            videos = load_participant(root, pid)
        except FileNotFoundError:
            continue
        med_a = np.median(np.concatenate([v["arousal"].to_numpy() for v in videos]))
        med_v = np.median(np.concatenate([v["valence"].to_numpy() for v in videos]))
        for vid, v in enumerate(videos):
            for start in range(0, len(v) - win + 1, step):
                w = v.iloc[start:start + win]
                a, val = w["arousal"].mean(), w["valence"].mean()
                rows.append({
                    "participant": pid, "video": vid, **window_features(w),
                    "arousal": a, "valence": val,
                    "label_arousal": int(a > med_a),
                    "label_fear": int(a > med_a and val < med_v),
                })
    return pd.DataFrame(rows)
