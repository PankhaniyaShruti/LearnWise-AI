"""Synthetic bootstrap dataset for learner mastery prediction.

This is labelled SYNTHETIC. Metrics from this data are for bootstrapping only
and are not production accuracy claims.
"""
from __future__ import annotations

import numpy as np

FEATURE_NAMES = [
    "accuracy",
    "attempts_log",
    "last_result",
    "consecutive_correct",
    "concept_difficulty",
    "revision_count",
    "hours_since_last",
    "rule_mastery",
]


def _rule_score(accuracy: float, last_result: int, consecutive: int) -> float:
    base = accuracy * 100
    recency = 5 if last_result == 1 else -5
    streak = min(max(consecutive, 0), 3) * 3
    return float(max(0, min(100, base + recency + streak))) / 100.0


def generate_synthetic(n: int = 1600, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows = []
    labels = []
    for _ in range(n):
        attempts = int(rng.integers(1, 18))
        accuracy = float(np.clip(rng.beta(2.2, 2.0), 0.05, 0.98))
        last_result = int(rng.random() < accuracy)
        consecutive = int(rng.integers(0, 6)) if last_result else 0
        difficulty = float(rng.uniform(0.2, 0.9))
        revision_count = int(rng.integers(0, 8))
        hours_since_last = float(rng.uniform(0.2, 240.0))
        rule = _rule_score(accuracy, last_result, consecutive)

        # Hidden "true mastery" process used only to label synthetic rows.
        latent = (
            0.45 * accuracy
            + 0.12 * min(attempts / 10.0, 1.0)
            + 0.10 * last_result
            + 0.08 * min(consecutive / 4.0, 1.0)
            - 0.14 * difficulty
            + 0.07 * min(revision_count / 5.0, 1.0)
            - 0.06 * min(hours_since_last / 168.0, 1.0)
            + 0.18 * rule
        )
        noise = float(rng.normal(0, 0.06))
        label = 1 if (latent + noise) >= 0.55 else 0
        rows.append(
            [
                accuracy,
                float(np.log1p(attempts)),
                float(last_result),
                float(min(consecutive, 6)),
                difficulty,
                float(revision_count),
                float(min(hours_since_last / 168.0, 1.5)),
                rule,
            ]
        )
        labels.append(label)
    return np.asarray(rows, dtype=float), np.asarray(labels, dtype=int)


def features_from_mastery_row(row: dict, difficulty: float = 0.5) -> list[float]:
    attempts = max(int(row.get("attempts") or 0), 0)
    correct = max(int(row.get("correct") or 0), 0)
    accuracy = (correct / attempts) if attempts else 0.0
    last_result = int(row.get("last_result") or 0)
    consecutive = int(row.get("consecutive_correct") or 0)
    rule = _rule_score(accuracy, last_result, consecutive)
    hours = 24.0
    next_review = row.get("next_review_at")
    updated = row.get("updated_at")
    if updated:
        try:
            from datetime import datetime, timezone

            when = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
            hours = max(0.0, (datetime.now(timezone.utc) - when).total_seconds() / 3600.0)
        except Exception:
            hours = 24.0
    return [
        accuracy,
        float(np.log1p(attempts)),
        float(last_result),
        float(min(consecutive, 6)),
        float(difficulty),
        0.0,
        float(min(hours / 168.0, 1.5)),
        rule,
    ]
