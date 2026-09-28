from __future__ import annotations

import uuid
from typing import Any

from .dataset import features_from_mastery_row
from .train import load_metrics, load_model

LABELS = [
    (0.20, "Needs Attention"),
    (0.40, "Weak"),
    (0.65, "Developing"),
    (0.85, "Strong"),
    (1.01, "Mastered"),
]


def probability_to_label(prob: float) -> str:
    for threshold, label in LABELS:
        if prob < threshold:
            return label
    return "Mastered"


def predict_concept(row: dict[str, Any], difficulty: float = 0.5) -> dict[str, Any]:
    model = load_model()
    feats = features_from_mastery_row(row, difficulty=difficulty)
    proba = float(model.predict_proba([feats])[0][1])
    return {
        "concept": row.get("concept"),
        "topic": row.get("topic"),
        "mastery_probability": round(proba, 4),
        "predicted_label": probability_to_label(proba),
        "rule_mastery_score": row.get("mastery_score"),
        "rule_mastery_label": row.get("mastery_label"),
        "features": {
            "accuracy": feats[0],
            "attempts_log": feats[1],
            "last_result": feats[2],
            "consecutive_correct": feats[3],
            "concept_difficulty": feats[4],
            "hours_since_last_scaled": feats[6],
            "rule_mastery": feats[7],
        },
    }


def predict_profile(user_email: str, concepts: list[dict[str, Any]]) -> dict[str, Any]:
    from ..knowledge.graph import find_concept_id, graph_payload
    from ..storage import get_store

    kg = {c["name"].lower(): c for c in graph_payload()["concepts"]}
    predictions = []
    for row in concepts:
        name = (row.get("concept") or "").lower()
        difficulty = 0.5
        match = kg.get(name)
        if not match:
            cid = find_concept_id(name)
            if cid:
                match = next((c for c in kg.values() if c["id"] == cid), None)
        if match:
            difficulty = float(match.get("difficulty") or 0.5)
        pred = predict_concept(row, difficulty=difficulty)
        predictions.append(pred)
        try:
            get_store().save_prediction(
                {
                    "id": str(uuid.uuid4()),
                    "user_email": user_email,
                    "concept": row.get("concept"),
                    "mastery_probability": pred["mastery_probability"],
                    "predicted_label": pred["predicted_label"],
                    "features": pred["features"],
                    "metrics": {"source": "synthetic_bootstrap_model"},
                }
            )
        except Exception:
            pass
    return {
        "model": "LogisticRegression",
        "dataset": "synthetic_bootstrap",
        "disclaimer": (
            "Predictions come from a model trained on a labelled synthetic dataset "
            "for bootstrapping. Do not treat these scores as production accuracy."
        ),
        "evaluation": load_metrics(),
        "predictions": predictions,
    }
