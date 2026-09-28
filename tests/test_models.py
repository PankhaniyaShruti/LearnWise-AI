import pytest
from pydantic import ValidationError

from backend.models import LearnRequest, LearnResponse, QuizQuestion, QuizSubmission


def test_quiz_question_requires_correct_option():
    with pytest.raises(ValidationError):
        QuizQuestion(
            question="Q",
            options=["a", "b", "c", "d"],
            correct_answer="e",
            concept_tested="x",
        )


def test_learn_request_mode_validation():
    req = LearnRequest(topic="  Photosynthesis  ", mode="Simple")
    assert req.topic == "Photosynthesis"
    assert req.mode == "simple"
    with pytest.raises(ValidationError):
        LearnRequest(topic="x", mode="nope")


def test_learn_response_concept_mapping():
    payload = {
        "explanation": "A complete explanation of the topic with enough text.",
        "key_concepts": ["A", "B", "C"],
        "quiz": [
            {
                "question": "Q1",
                "options": ["A1", "A2", "A3", "A4"],
                "correct_answer": "A1",
                "concept_tested": "A",
            },
            {
                "question": "Q2",
                "options": ["B1", "B2", "B3", "B4"],
                "correct_answer": "B2",
                "concept_tested": "B",
            },
            {
                "question": "Q3",
                "options": ["C1", "C2", "C3", "C4"],
                "correct_answer": "C3",
                "concept_tested": "C",
            },
        ],
    }
    LearnResponse(**payload)
    payload["quiz"][2]["concept_tested"] = "A"
    with pytest.raises(ValidationError):
        LearnResponse(**payload)


def test_quiz_submission_shape():
    QuizSubmission(
        session_id="abc",
        user_email="a@b.com",
        answers=[{"question_index": 0, "selected_answer": "x"}],
    )
