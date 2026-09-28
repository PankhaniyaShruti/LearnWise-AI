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
