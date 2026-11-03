import numpy as np
import pandas as pd

from features import FEATURES, HZ, window_features


def make_window(yaw_step=0.0, hr=70.0, n=125):
    return pd.DataFrame({
        "pitch": np.zeros(n),
        "yaw": (np.arange(n) * yaw_step) % 360 - 180,
        "hr": np.full(n, hr),
    })


def test_still_head_has_zero_speed():
    f = window_features(make_window())
    assert f["head_speed_mean"] == 0
    assert set(f) == set(FEATURES)


def test_yaw_wraparound_does_not_create_spike():
    f = window_features(make_window(yaw_step=10.0))
    assert abs(f["head_speed_max"] - 10.0 * HZ) < 1e-6


def test_hr_slope_is_positive_for_rising_hr():
    w = make_window()
    w["hr"] = 70 + np.arange(len(w)) / HZ
    assert abs(window_features(w)["hr_slope"] - 1.0) < 1e-6
