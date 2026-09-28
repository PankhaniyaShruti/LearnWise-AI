from backend.ml.dataset import generate_synthetic
from backend.ml.predict import predict_concept, probability_to_label
from backend.ml.train import train_and_evaluate


def test_train_and_predict(tmp_path, monkeypatch):
    monkeypatch.setenv("ML_ARTIFACT_DIR", str(tmp_path))
    from backend import config
    from backend.ml import train as train_mod

    train_mod.MODEL_PATH = tmp_path / "mastery_logreg.joblib"
    train_mod.METRICS_PATH = tmp_path / "metrics.json"
    metrics = train_and_evaluate(n=400, seed=3)
    assert metrics["dataset"] == "synthetic_bootstrap"
    assert "disclaimer" in metrics
    for key in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
        assert key in metrics
    X, y = generate_synthetic(n=20, seed=3)
    assert X.shape[1] == 8
    pred = predict_concept(
        {
            "concept": "Precision",
            "attempts": 6,
            "correct": 5,
            "consecutive_correct": 2,
            "last_result": 1,
            "mastery_score": 88,
            "mastery_label": "Strong",
        },
        difficulty=0.55,
    )
    assert 0 <= pred["mastery_probability"] <= 1
    assert pred["predicted_label"] in {
        "Needs Attention",
        "Weak",
        "Developing",
        "Strong",
        "Mastered",
    }
    assert probability_to_label(0.1) == "Needs Attention"
