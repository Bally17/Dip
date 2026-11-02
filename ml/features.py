"""Načítanie CEAP-360VR (Frame dáta, 25 Hz) a výpočet príznakov v oknách."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HZ = 25
WINDOW_S = 5
STEP_S = 2.5

FEATURES = [
    "hr_mean", "hr_std", "hr_slope",
    "head_speed_mean", "head_speed_std", "head_speed_max",
    "head_pitch_std", "head_yaw_std",
]


def _load(root: Path, folder: str, pid: int, suffix: str, key: str) -> list:
    pname = f"P{pid}"
    path = root / folder / "Frame" / f"{pname}_{suffix}_FrameData.json"
    return json.loads(path.read_text())[key][0]


def load_participant(root: Path, pid: int) -> list[pd.DataFrame]:
    """Vráti jeden DataFrame na video: tep, pohyb hlavy a arousal na spoločnej osi 25 Hz."""
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
        arousal = pd.DataFrame(a["TimeStamp_Valence_Arousal"])
        n = min(len(hm), len(hr), len(arousal))
        videos.append(pd.DataFrame({
            "t": hm["TimeStamp"].to_numpy()[:n],
            "pitch": hm["Pitch"].to_numpy()[:n],
            "yaw": hm["Yaw"].to_numpy()[:n],
            "hr": hr["HR"].to_numpy()[:n],
            "arousal": arousal["Arousal"].to_numpy()[:n],
        }))
    return videos


def window_features(w: pd.DataFrame) -> dict:
    """Príznaky jedného okna. Uhlová rýchlosť hlavy v °/s, yaw sa zalamuje na ±180°."""
    dyaw = (np.diff(w["yaw"].to_numpy()) + 180) % 360 - 180
    dpitch = np.diff(w["pitch"].to_numpy())
    speed = np.hypot(dyaw, dpitch) * HZ
    hr = w["hr"].to_numpy()
    x = np.arange(len(hr)) / HZ
    return {
        "hr_mean": hr.mean(),
        "hr_std": hr.std(),
        "hr_slope": np.polyfit(x, hr, 1)[0],
        "head_speed_mean": speed.mean(),
        "head_speed_std": speed.std(),
        "head_speed_max": speed.max(),
        "head_pitch_std": w["pitch"].std(),
        "head_yaw_std": np.std(np.unwrap(np.radians(w["yaw"])) * 180 / np.pi),
    }


def build_dataset(root: Path, participants=range(1, 33)) -> pd.DataFrame:
    """Jeden riadok = jedno okno. Label: arousal okna nad mediánom účastníka (1) alebo pod ním (0)."""
    win, step = int(WINDOW_S * HZ), int(STEP_S * HZ)
    rows = []
    for pid in participants:
        try:
            videos = load_participant(root, pid)
        except FileNotFoundError:
            continue
        median = np.median(np.concatenate([v["arousal"].to_numpy() for v in videos]))
        for vid, v in enumerate(videos):
            for start in range(0, len(v) - win + 1, step):
                w = v.iloc[start:start + win]
                rows.append({
                    "participant": pid, "video": vid, **window_features(w),
                    "arousal": w["arousal"].mean(),
                    "label": int(w["arousal"].mean() > median),
                })
    return pd.DataFrame(rows)
