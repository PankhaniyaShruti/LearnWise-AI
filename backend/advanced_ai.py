"""Advanced AI features routed through the LLM gateway with Pydantic validation."""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .llm.gateway import complete, extract_json
from .models import QuizQuestion

logger = logging.getLogger(__name__)


class TutorReply(BaseModel):
    strategy: str = Field(..., min_length=1)
    reply: str = Field(..., min_length=1)


class RevisionLesson(BaseModel):
    explanation: str = Field(..., min_length=1)
    key_concepts: list[str] = Field(default_factory=list)
    quiz: list[QuizQuestion] = Field(..., min_length=3, max_length=12)


class QuizEnvelope(BaseModel):
    quiz: list[QuizQuestion] = Field(..., min_length=3)


class Flashcard(BaseModel):
    front: str
    back: str
    concept: str = ""


class FlashcardEnvelope(BaseModel):
    cards: list[Flashcard] = Field(..., min_length=1)


class PathItem(BaseModel):
    order: int | None = None
    title: str
    description: str = ""
    status: str = "not_started"


class LearningPath(BaseModel):
    title: str = ""
    items: list[PathItem] = Field(..., min_length=1)


class PlanDay(BaseModel):
    day: int | None = None
    focus: str = ""
    lesson_minutes: int | None = None
    quiz_minutes: int | None = None
    notes: str = ""


class StudyPlanEnvelope(BaseModel):
    plan: list[PlanDay] = Field(..., min_length=1)


def _complete_json(
    system: str,
    user: str,
    *,
    feature: str,
    prompt_name: str,
    prompt_version: str,
    schema: type[BaseModel],
    user_email: str | None,
    task: str,
    max_tokens: int,
    temperature: float = 0.3,
) -> BaseModel:
    _result, parsed = complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        feature=feature,
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        user_email=user_email,
        task=task,
        temperature=temperature,
        max_tokens=max_tokens,
        schema=schema,
    )
    return parsed


def tutor_respond(
    topic: str,
    concept: str | None,
    action: str,
    context: str | None,
    previous_strategies: list[str] | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    previous_strategies = previous_strategies or []
    action = (action or "explain_simply").strip().lower()
    strategy_map = {
        "explain_simply": "Use simple language a beginner understands. Short paragraphs.",
        "explain_with_analogy": "Explain using one clear real-world analogy.",
        "give_example": "Give one concrete worked example.",
        "explain_technically": "Use precise technical language and structure.",
        "give_hint": "Give a hint only — do not reveal the full answer.",
        "quiz_me": "Ask one short open question to check understanding. Do not answer it.",
        "why_important": "Explain why this matters in practice or further learning.",
        "still_dont_understand": "The learner still does not understand. Use a DIFFERENT strategy than before.",
    }
    instruction = strategy_map.get(action, strategy_map["explain_simply"])
    avoid = ""
    version = "v2" if action == "still_dont_understand" else "v1"
    if action == "still_dont_understand" and previous_strategies:
        avoid = f" Do NOT reuse these approaches: {', '.join(previous_strategies)}. Pick a fresh angle."
    system = (
        "You are LearnWise AI Tutor. Return ONLY valid JSON: "
        '{"strategy":"short strategy name","reply":"your teaching response"}'
    )
    user = (
        f"Topic: {topic}\n"
        f"Concept focus: {concept or 'general'}\n"
        f"Action: {action}\n"
        f"Instruction: {instruction}{avoid}\n"
        f"Lesson context (optional):\n{(context or '')[:1500]}\n"
    )
    parsed = _complete_json(
        system,
        user,
        feature="tutor",
        prompt_name="tutor",
        prompt_version=version,
        schema=TutorReply,
        user_email=user_email,
        task="tutor",
        max_tokens=1200,
    )
    return {"strategy": parsed.strategy or action, "reply": parsed.reply, "action": action}


def generate_revision_lesson(
    topic: str, weak_concepts: list[str], user_email: str | None = None
) -> dict[str, Any]:
    concepts = weak_concepts[:5] or ["core ideas"]
    system = (
        "You are LearnWise revision coach. Return ONLY JSON with keys: "
        "explanation (string), key_concepts (exactly 3 strings from the weak list if possible), "
        "quiz (exactly 3 objects with question, options[4], correct_answer, concept_tested). "
        "Focus only on the weak concepts."
    )
    user = (
        f"Topic: {topic}\n"
        f"Weak concepts to revise: {', '.join(concepts)}\n"
        "Write a targeted revision explanation (under 350 words) and a diagnostic 3-question quiz."
    )
    try:
        parsed = _complete_json(
            system,
            user,
            feature="revision",
            prompt_name="revision",
            prompt_version="v1",
            schema=RevisionLesson,
            user_email=user_email,
            task="learn",
            max_tokens=2500,
        )
        data = parsed.model_dump()
    except Exception:
        # Relaxed fallback if concept mapping is strict
        result = complete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            feature="revision",
            prompt_name="revision",
            prompt_version="v1",
            user_email=user_email,
            task="learn",
            max_tokens=2500,
        )
        raw = extract_json(result.text)
        if not isinstance(raw, dict) or "explanation" not in raw or "quiz" not in raw:
            raise RuntimeError("Revision missing required fields.")
        data = raw
        data.setdefault("key_concepts", concepts[:3])
    if not data.get("key_concepts"):
        data["key_concepts"] = concepts[:3]
    return data


def generate_adaptive_quiz(
    topic: str,
    focus_concepts: list[str],
    difficulty: str = "medium",
    user_email: str | None = None,
) -> list[dict[str, Any]]:
    difficulty = (difficulty or "medium").lower()
    if difficulty not in {"easy", "medium", "hard"}:
        difficulty = "medium"
    focus = focus_concepts[:5] or ["core ideas"]
    system = (
        "Return ONLY JSON: {\"quiz\":[...]} with exactly 3 questions. "
        "Each question: question, options (4), correct_answer (exact option), concept_tested. "
        f"Difficulty target: {difficulty}."
    )
    user = (
        f"Topic: {topic}\n"
        f"Prioritize these weak/focus concepts: {', '.join(focus)}\n"
        "Create 3 multiple-choice diagnostic questions."
    )
    parsed = _complete_json(
        system,
        user,
        feature="adaptive_quiz",
        prompt_name="quiz",
        prompt_version="v1",
        schema=QuizEnvelope,
        user_email=user_email,
        task="quiz",
        max_tokens=2000,
    )
    return [q.model_dump() for q in parsed.quiz[:3]]


def generate_flashcards(
    topic: str, concepts: list[str] | None = None, user_email: str | None = None
) -> list[dict[str, str]]:
    concepts = concepts or []
    system = (
        "Return ONLY JSON: {\"cards\":[{\"front\":\"question\",\"back\":\"answer\",\"concept\":\"...\"}]}. "
        "Exactly 6 cards."
    )
    user = f"Topic: {topic}\nConcepts: {', '.join(concepts) if concepts else 'core ideas'}\n"
    parsed = _complete_json(
        system,
        user,
        feature="flashcards",
        prompt_name="flashcards",
        prompt_version="v1",
        schema=FlashcardEnvelope,
        user_email=user_email,
        task="simple",
        max_tokens=1800,
    )
    return [c.model_dump() for c in parsed.cards[:6]]


def generate_learning_path(topic: str, user_email: str | None = None) -> dict[str, Any]:
    system = (
        "Return ONLY JSON: {\"title\": \"...\", \"items\": [{\"order\":1,\"title\":\"...\",\"description\":\"...\"}]}. "
        "Provide 6 to 8 sequential learning steps for a beginner-to-intermediate path."
    )
    user = f"Create a structured learning path for: {topic}"
    parsed = _complete_json(
        system,
        user,
        feature="learning_path",
        prompt_name="path",
        prompt_version="v1",
        schema=LearningPath,
        user_email=user_email,
        task="planner",
        max_tokens=1800,
    )
    items = []
    for i, item in enumerate(parsed.items):
        dumped = item.model_dump()
        dumped.setdefault("order", i + 1)
        dumped.setdefault("status", "not_started")
        items.append(dumped)
    return {"title": parsed.title or topic, "topic": topic, "items": items}


def generate_study_plan(
    exam_name: str,
    exam_date: str,
    daily_minutes: int,
    level: str,
    topics: list[str],
    user_email: str | None = None,
) -> dict[str, Any]:
    system = (
        "Return ONLY JSON: {\"plan\":[{\"day\":1,\"focus\":\"...\",\"lesson_minutes\":45,\"quiz_minutes\":15,\"notes\":\"...\"}]}. "
        "Create a practical multi-day plan."
    )
    user = (
        f"Exam: {exam_name}\nDate: {exam_date}\nDaily study minutes: {daily_minutes}\n"
        f"Level: {level}\nTopics: {', '.join(topics)}\n"
        "Plan day-by-day using the daily time budget."
    )
    parsed = _complete_json(
        system,
        user,
        feature="study_plan",
        prompt_name="planner",
        prompt_version="v1",
        schema=StudyPlanEnvelope,
        user_email=user_email,
        task="planner",
        max_tokens=2000,
    )
    return {
        "exam_name": exam_name,
        "exam_date": exam_date,
        "daily_minutes": daily_minutes,
        "level": level,
        "topics": topics,
        "plan": [d.model_dump() for d in parsed.plan],
    }
