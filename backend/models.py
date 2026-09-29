from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal


LEARNING_MODES = {
    "simple",
    "detailed",
    "study",
    "story",
    "exam",
    "practical",
}


class QuizQuestion(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="The multiple choice question",
    )
    options: list[str] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Exactly 4 unique options",
    )
    correct_answer: str = Field(
        ...,
        min_length=1,
        description="The correct option",
    )
    concept_tested: str = Field(
        ...,
        min_length=1,
        description="The exact key concept tested",
    )
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    explanation: str = Field(
        default="",
        description="Explanation of why the correct answer is right",
    )

    @field_validator("question", "correct_answer", "concept_tested")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot contain only whitespace.")
        return value

    @field_validator("options")
    @classmethod
    def validate_options(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("Quiz options cannot be empty.")

        normalized = [value.casefold() for value in cleaned]

        if len(set(normalized)) != len(normalized):
            raise ValueError("Quiz options must be unique.")

        return cleaned

    @field_validator("explanation")
    @classmethod
    def normalize_explanation(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def check_correct_answer(self):
        if self.correct_answer not in self.options:
            raise ValueError(
                "correct_answer must exactly match one of the options."
            )
        return self


class LearnResponse(BaseModel):
    explanation: str = Field(
        ...,
        min_length=1,
        description="Complete teaching explanation",
    )
    key_concepts: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly 3 distinct key concepts",
    )
    quiz: list[QuizQuestion] = Field(
        ...,
        min_length=3,
        max_length=15,
        description="Topic-appropriate quiz questions",
    )

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Explanation cannot contain only whitespace.")
        return value

    @field_validator("key_concepts")
    @classmethod
    def validate_key_concepts(cls, concepts: list[str]) -> list[str]:
        cleaned = [concept.strip() for concept in concepts]

        if any(not concept for concept in cleaned):
            raise ValueError("Key concepts cannot be empty.")

        normalized = [concept.casefold() for concept in cleaned]

        if len(set(normalized)) != len(normalized):
            raise ValueError("Key concepts must be distinct.")

        return cleaned

    @model_validator(mode="after")
    def check_concepts_match(self):
        concepts = set(self.key_concepts)

        for index, question in enumerate(self.quiz):
            if question.concept_tested not in concepts:
                raise ValueError(
                    f"Question {index + 1} tests "
                    f"'{question.concept_tested}', which is not in key_concepts."
                )

        tested = {question.concept_tested for question in self.quiz}

        if tested != concepts:
            raise ValueError(
                "Every key concept must be tested by at least one question."
            )

        return self


class LearnRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    mode: str = Field(default="simple")
    user_email: str = Field(default="guest@learnwise.com")

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Topic cannot be empty.")
        return value

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in LEARNING_MODES:
            raise ValueError(
                "Mode must be one of: " + ", ".join(sorted(LEARNING_MODES))
            )
        return value


class HistoryItem(BaseModel):
    session_id: str
    topic: str
    mode: str
    explanation: str
    key_concepts: list[str]
    quiz: list[QuizQuestion]
    created_at: str


class QuizAnswer(BaseModel):
    question_index: int = Field(..., ge=0)
    selected_answer: str


class QuizSubmission(BaseModel):
    session_id: str
    user_email: str = Field(default="guest@learnwise.com")
    answers: list[QuizAnswer]


class QuizResult(BaseModel):
    topic: str
    score: int = Field(..., ge=0)
    total: int = Field(..., ge=1)
    percentage: int = Field(..., ge=0, le=100)
    weak_concepts: list[str] = Field(default_factory=list)


class TutorRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    action: str = Field(default="explain_simply")
    concept: str | None = None
    context: str | None = None
    previous_strategies: list[str] = Field(default_factory=list)
    user_email: str = Field(default="guest@learnwise.com")


class RevisionRequest(BaseModel):
    user_email: str = Field(default="guest@learnwise.com")
    topic: str | None = None


class AdaptiveQuizRequest(BaseModel):
    user_email: str = Field(default="guest@learnwise.com")
    topic: str = Field(..., min_length=1)
    difficulty: str = Field(default="medium")


class AdaptiveQuizSubmit(BaseModel):
    user_email: str = Field(default="guest@learnwise.com")
    topic: str
    quiz: list[QuizQuestion]
    answers: list[QuizAnswer]


class FlashcardsRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    concepts: list[str] = Field(default_factory=list)
    user_email: str = Field(default="guest@learnwise.com")


class LearningPathRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    user_email: str = Field(default="guest@learnwise.com")





class RagAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_email: str = Field(default="guest@learnwise.com")
    document_ids: list[str] | None = None


class AgentRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    user_email: str = Field(default="guest@learnwise.com")
    topic: str | None = None


class RecommendRequest(BaseModel):
    user_email: str = Field(default="guest@learnwise.com")
    exam_date: str | None = None
    learning_goal: str | None = None