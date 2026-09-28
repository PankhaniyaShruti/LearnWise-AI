from backend.mastery import apply_quiz_to_mastery, compute_score, get_mastery_profile, mastery_label


def test_compute_score_bounds():
    assert compute_score(0, 0, 0, 0) == 0
    assert 0 <= compute_score(10, 10, 5, 1) <= 100
    assert compute_score(4, 4, 3, 1) == 100


def test_labels():
    assert mastery_label(10) == "Needs Attention"
    assert mastery_label(50) == "Weak"
    assert mastery_label(70) == "Developing"
    assert mastery_label(85) == "Strong"
    assert mastery_label(95) == "Mastered"


def test_apply_quiz_updates_store(store):
    quiz = [
        {
            "question": "q1",
            "options": ["a", "b", "c", "d"],
            "correct_answer": "a",
            "concept_tested": "Precision",
        },
        {
            "question": "q2",
            "options": ["a", "b", "c", "d"],
            "correct_answer": "b",
            "concept_tested": "Recall",
        },
    ]
    apply_quiz_to_mastery("user@test.com", "ML", quiz, {0: "a", 1: "a"})
    profile = get_mastery_profile("user@test.com")
    assert profile["total_concepts"] == 2
    names = {c["concept"]: c for c in profile["concepts"]}
    assert names["Precision"]["mastery_score"] > names["Recall"]["mastery_score"]
    assert "Recall" in [c["concept"] for c in profile["weak_concepts"]]
