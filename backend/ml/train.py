"""Train and evaluate the mastery classifier on the synthetic bootstrap set."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..config import ML_ARTIFACT_DIR
from .dataset import FEATURE_NAMES, generate_synthetic

MODEL_PATH = ML_ARTIFACT_DIR / "mastery_logreg.joblib"
METRICS_PATH = ML_ARTIFACT_DIR / "metrics.json"


def train_and_evaluate(n: int = 1600, seed: int = 7) -> dict:
    X, y = generate_synthetic(n=n, seed=seed)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(max_iter=400, class_weight="balanced", random_state=seed),
            ),
        ]
    )
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    metrics = {
        "dataset": "synthetic_bootstrap",
        "disclaimer": "Metrics are from synthetic data used to bootstrap the model. They are not production results.",
        "n_samples": int(len(y)),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "features": FEATURE_NAMES,
        "model": "LogisticRegression",
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "precision": round(float(precision_score(y_test, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, pred, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        "positive_rate_test": round(float(np.mean(y_test)), 4),
    }
    ML_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def load_model():
    if not MODEL_PATH.exists():
        train_and_evaluate()
    return joblib.load(MODEL_PATH)


def load_metrics() -> dict:
    if not METRICS_PATH.exists():
        train_and_evaluate()
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(json.dumps(train_and_evaluate(), indent=2))
