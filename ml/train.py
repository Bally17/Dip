"""Trénovanie a vyhodnotenie po účastníkoch (leave-one-subject-out)."""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import FEATURES, build_dataset

MODELS = {
    "logreg": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
    "rf": lambda: RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0, n_jobs=-1),
}


def evaluate(df, make_model) -> dict:
    X, y, groups = df[FEATURES].to_numpy(), df["label"].to_numpy(), df["participant"].to_numpy()
    scores = []
    for train, test in LeaveOneGroupOut().split(X, y, groups):
        if len(np.unique(y[test])) < 2:
            continue
        model = make_model().fit(X[train], y[train])
        proba = model.predict_proba(X[test])[:, 1]
        scores.append((
            accuracy_score(y[test], proba > 0.5),
            f1_score(y[test], proba > 0.5),
            roc_auc_score(y[test], proba),
        ))
    acc, f1, auc = np.array(scores).T
    return {
        "participants": len(scores),
        "accuracy": [acc.mean(), acc.std()],
        "f1": [f1.mean(), f1.std()],
        "roc_auc": [auc.mean(), auc.std()],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True, help="priečinok CEAP-360VR")
    ap.add_argument("--out", type=Path, default=Path("artifacts"))
    args = ap.parse_args()

    df = build_dataset(args.data)
    print(f"okná: {len(df)}, účastníci: {df['participant'].nunique()}, podiel label=1: {df['label'].mean():.2f}")
    args.out.mkdir(exist_ok=True)
    results = {name: evaluate(df, make) for name, make in MODELS.items()}
    for name, r in results.items():
        print(name, {k: (np.round(v, 3).tolist() if isinstance(v, list) else v) for k, v in r.items()})
    (args.out / "metrics.json").write_text(json.dumps(results, indent=2))

    best = max(results, key=lambda n: results[n]["roc_auc"][0])
    model = MODELS[best]().fit(df[FEATURES].to_numpy(), df["label"].to_numpy())
    joblib.dump({"model": model, "features": FEATURES, "name": best}, args.out / "model.joblib")
    print("uložený model:", best)


if __name__ == "__main__":
    main()
