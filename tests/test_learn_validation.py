import pytest
from pydantic import ValidationError

from backend.models import LearnResponse, QuizQuestion


CONCEPTS = [
    "Python variables",
    "Variable assignment",
    "Variable naming",
]


def make_question(concept, index=0):
    return {
        "question": f"Question {index + 1}?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "Option A",
        "concept_tested": concept,
        "difficulty": "easy",
        "explanation": "Option A is correct because it matches the concept.",
    }


def make_lesson(question_count=3):
    quiz = [
        make_question(CONCEPTS[index % 3], index)
        for index in range(question_count)
    ]

    return {
        "explanation": "A complete lesson about Python variables.",
        "key_concepts": CONCEPTS.copy(),
        "quiz": quiz,
    }


@pytest.mark.parametrize("question_count", [3, 4, 5, 8, 15])
def test_valid_dynamic_quiz_lengths(question_count):
    lesson = LearnResponse.model_validate(make_lesson(question_count))

    assert len(lesson.quiz) == question_count


def test_correct_answer_must_match_option():
    question = make_question(CONCEPTS[0])
    question["correct_answer"] = "Not an option"

    with pytest.raises(ValidationError):
        QuizQuestion.model_validate(question)


def test_duplicate_options_are_rejected():
    question = make_question(CONCEPTS[0])
    question["options"] = [
        "Option A",
        "Option B",
        "option a",
        "Option D",
    ]

    with pytest.raises(ValidationError):
        QuizQuestion.model_validate(question)


def test_empty_option_is_rejected():
    question = make_question(CONCEPTS[0])
    question["options"][1] = "   "

    with pytest.raises(ValidationError):
        QuizQuestion.model_validate(question)


def test_unknown_concept_is_rejected():
    lesson = make_lesson()
    lesson["quiz"][0]["concept_tested"] = "Unknown concept"

    with pytest.raises(ValidationError):
        LearnResponse.model_validate(lesson)


def test_every_concept_must_be_tested():
    lesson = make_lesson()

    for question in lesson["quiz"]:
        question["concept_tested"] = CONCEPTS[0]

    with pytest.raises(ValidationError):
        LearnResponse.model_validate(lesson)


def test_duplicate_key_concepts_are_rejected():
    lesson = make_lesson()
    lesson["key_concepts"] = [
        "Python variables",
        "python variables",
        "Variable naming",
    ]

    with pytest.raises(ValidationError):
        LearnResponse.model_validate(lesson)


def test_whitespace_only_explanation_is_rejected():
    lesson = make_lesson()
    lesson["explanation"] = "   "

    with pytest.raises(ValidationError):
        LearnResponse.model_validate(lesson)


def test_whitespace_is_normalized():
    question = make_question(CONCEPTS[0])
    question["question"] = "  What is a variable?  "
    question["options"] = [
        " A ",
        " B ",
        " C ",
        " D ",
    ]
    question["correct_answer"] = "A"

    validated = QuizQuestion.model_validate(question)

    assert validated.question == "What is a variable?"
    assert validated.options == ["A", "B", "C", "D"]
    assert validated.correct_answer == "A"


def test_more_than_fifteen_questions_are_rejected():
    lesson = make_lesson(16)

    with pytest.raises(ValidationError):
        LearnResponse.model_validate(lesson)