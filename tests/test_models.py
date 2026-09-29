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
    concepts = ["A", "B", "C"]

    quiz = [
        {
            "question": f"Q{i + 1}",
            "options": ["A1", "A2", "A3", "A4"],
            "correct_answer": "A1",
            "concept_tested": concepts[i % 3],
            "difficulty": ["easy", "medium", "hard"][i % 3],
            "explanation": f"Explanation for question {i + 1}.",
        }
        for i in range(10)
    ]

    payload = {
        "explanation": "A complete explanation of the topic with enough text.",
        "key_concepts": concepts,
        "quiz": quiz,
    }

    response = LearnResponse(**payload)

    assert len(response.quiz) == 10
    assert {question.concept_tested for question in response.quiz} == set(concepts)

    payload["quiz"][9]["concept_tested"] = "Unknown"
    with pytest.raises(ValidationError):
        LearnResponse(**payload)

def test_quiz_submission_shape():
    QuizSubmission(
        session_id="abc",
        user_email="a@b.com",
        answers=[{"question_index": 0, "selected_answer": "x"}],
    )
