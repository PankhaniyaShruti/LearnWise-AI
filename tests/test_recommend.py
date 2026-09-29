from backend.recommend.engine import recommend_next_action


def test_onboard_when_no_mastery():
    rec = recommend_next_action(
        mastery={"total_concepts": 0, "overall_mastery": 0, "weak_concepts": [], "critical_concepts": [], "due_for_review": [], "concepts": []},
        progress={"total_sessions": 0, "total_quiz_attempts": 0},
    )
    assert rec["kind"] == "onboard"


def test_critical_revision_action():
    rec = recommend_next_action(
        mastery={
            "total_concepts": 2,
            "overall_mastery": 40,
            "weak_concepts": [{"concept": "Recall", "mastery_score": 30}],
            "critical_concepts": [{"concept": "Precision", "mastery_score": 20}],
            "due_for_review": [],
            "concepts": [{"concept": "Precision", "mastery_score": 20}],
        },
        progress={"total_sessions": 3, "total_quiz_attempts": 3},
    )
    assert rec["kind"] == "critical"
    assert "Precision" in rec["action"]


def test_prerequisite_gap_wins():
    rec = recommend_next_action(
        mastery={
            "total_concepts": 1,
            "overall_mastery": 40,
            "weak_concepts": [{"concept": "Logistic Regression", "mastery_score": 35}],
            "critical_concepts": [],
            "due_for_review": [],
            "concepts": [{"concept": "Logistic Regression", "mastery_score": 35}],
        },
        progress={},
        prerequisite_gaps=[{"name": "Probability", "distance": 1}],
    )
    assert rec["kind"] == "prerequisite"
    assert "Probability" in rec["action"]

def test_rag_practice_requires_ready_document():

    rec = recommend_next_action(
        mastery={
            "total_concepts": 2,
            "overall_mastery": 50,
            "weak_concepts": [
                {"concept": "Neural Networks", "mastery_score": 40}
            ],
            "critical_concepts": [],
            "due_for_review": [],
            "concepts": [
                {"concept": "Neural Networks", "mastery_score": 40}
            ],
        },
        progress={},
        documents=[
            {"id": "doc-1", "status": "processing"}
        ],
    )

    assert rec["kind"] != "rag_practice"
    assert rec["documents_available"] == 0


def test_rag_practice_with_ready_document():

    rec = recommend_next_action(
        mastery={
            "total_concepts": 2,
            "overall_mastery": 50,
            "weak_concepts": [
                {"concept": "Neural Networks", "mastery_score": 40}
            ],
            "critical_concepts": [],
            "due_for_review": [],
            "concepts": [
                {"concept": "Neural Networks", "mastery_score": 40}
            ],
        },
        progress={},
        documents=[
            {"id": "doc-1", "status": "ready"}
        ],
    )

    assert rec["kind"] == "rag_practice"
    assert rec["documents_available"] == 1
    assert "Neural Networks" in rec["action"]

def test_ml_weak_prediction_influences_recommendation():
    rec = recommend_next_action(
        mastery={
            "total_concepts": 3,
            "overall_mastery": 65,
            "weak_concepts": [],
            "critical_concepts": [],
            "due_for_review": [],
            "concepts": [
                {"concept": "Python Basics", "mastery_score": 20},
                {"concept": "Neural Networks", "mastery_score": 80},
            ],
        },
        progress={},
        ml_predictions=[
            {
                "concept": "Neural Networks",
                "predicted_label": "Needs Attention",
            }
        ],
    )

    assert rec["focus_concept"] == "Neural Networks"
    assert rec["kind"] == "default"
    assert "Neural Networks" in rec["action"]

def test_exam_recommendation_for_near_exam():
    from datetime import datetime, timedelta, timezone

    exam_date = (
        datetime.now(timezone.utc) + timedelta(days=5)
    ).isoformat()

    rec = recommend_next_action(
        mastery={
            "total_concepts": 2,
            "overall_mastery": 55,
            "weak_concepts": [
                {"concept": "Machine Learning", "mastery_score": 35}
            ],
            "critical_concepts": [],
            "due_for_review": [],
            "concepts": [
                {"concept": "Machine Learning", "mastery_score": 35}
            ],
        },
        progress={},
        exam_date=exam_date,
    )

    assert rec["kind"] == "exam"
    assert rec["focus_concept"] == "Machine Learning"
    assert rec["exam_days_remaining"] <= 5