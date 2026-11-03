"""Trénovanie a vyhodnotenie po účastníkoch (leave-one-subject-out) pre dva labely.

Jeden príkaz vytvorí model_arousal.joblib, model_fear.joblib, model.joblib (kópia fear) a metrics.json:
    python train.py --data <CEAP-360VR> --out artifacts
"""
import argparse
import json
import shutil
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import FEATURES, build_dataset

LABELS = {"arousal": "label_arousal", "fear": "label_fear"}

MODELS = {
    "logreg_c0.1": lambda: make_pipeline(
        StandardScaler(), LogisticRegression(C=0.1, class_weight="balanced", max_iter=2000)),
    "logreg_c1": lambda: make_pipeline(
        StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000)),
    "rf_leaf5": lambda: RandomForestClassifier(
        n_estimators=300, min_samples_leaf=5, class_weight="balanced_subsample", random_state=0, n_jobs=-1),
    "rf_leaf20": lambda: RandomForestClassifier(
        n_estimators=300, min_samples_leaf=20, class_weight="balanced_subsample", random_state=0, n_jobs=-1),
    "hgb_d3": lambda: HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=150, l2_regularization=1.0,
        class_weight="balanced", random_state=0),
    "hgb_d6": lambda: HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.03, max_iter=200, min_samples_leaf=40, l2_regularization=5.0,
        class_weight="balanced", random_state=0),
}


def _ms(values) -> list[float]:
    values = np.asarray(values)
    return [round(float(values.mean()), 4), round(float(values.std()), 4)]


def evaluate(df, label: str, make_model) -> dict:
    """LOSO: model sa vždy trénuje bez jediného účastníka a testuje len na ňom."""
    X, y, groups = df[FEATURES].to_numpy(), df[label].to_numpy(), df["participant"].to_numpy()
    acc, f1, auc, base = [], [], [], []
    for train, test in LeaveOneGroupOut().split(X, y, groups):
        if len(np.unique(y[test])) < 2:
            continue
        model = make_model().fit(X[train], y[train])
        proba = model.predict_proba(X[test])[:, 1]
        acc.append(accuracy_score(y[test], proba > 0.5))
        f1.append(f1_score(y[test], proba > 0.5, zero_division=0))
        auc.append(roc_auc_score(y[test], proba))
        base.append(max(y[test].mean(), 1 - y[test].mean()))
    return {
        "participants": len(auc),
        "accuracy": _ms(acc), "f1": _ms(f1), "roc_auc": _ms(auc),
        "majority_accuracy": _ms(base),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True, help="priečinok CEAP-360VR")
    ap.add_argument("--out", type=Path, default=Path("artifacts"))
    args = ap.parse_args()

    df = build_dataset(args.data)
    print(f"okná: {len(df)}, účastníci: {df['participant'].nunique()}")
    args.out.mkdir(exist_ok=True)

    metrics = {}
    for name, label in LABELS.items():
        print(f"\n== {name} (podiel pozitívnych: {df[label].mean():.2f})")
        results = {}
        for model_name, make in MODELS.items():
            results[model_name] = evaluate(df, label, make)
            r = results[model_name]
            print(f"{model_name:12s} AUC {r['roc_auc'][0]:.3f}±{r['roc_auc'][1]:.3f}  "
                  f"F1 {r['f1'][0]:.3f}  acc {r['accuracy'][0]:.3f} (väčšina {r['majority_accuracy'][0]:.3f})")
        best = max(results, key=lambda n: results[n]["roc_auc"][0])
        model = MODELS[best]().fit(df[FEATURES].to_numpy(), df[label].to_numpy())
        joblib.dump({"model": model, "features": FEATURES, "name": best}, args.out / f"model_{name}.joblib")
        metrics[name] = {
            "positive_rate": round(float(df[label].mean()), 4),
            "best": best,
            "models": results,
        }
        print("vybraný:", best)

    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    shutil.copyfile(args.out / "model_fear.joblib", args.out / "model.joblib")


if __name__ == "__main__":
    main()
