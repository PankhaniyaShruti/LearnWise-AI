"""Specialized agents plus a planner that routes instead of calling every tool."""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from ..knowledge.graph import recommended_next_concepts
from ..llm.gateway import complete
from ..mastery import get_mastery_profile
from ..rag.pipeline import ask_documents, list_user_documents, retrieve_for_user
from ..recommend.engine import recommend_next_action
from ..storage import get_store


class RouteDecision(BaseModel):
    intent: str = Field(..., description="primary intent")
    tools: list[str] = Field(default_factory=list)
    topic: str | None = None
    notes: str | None = None


TUTOR_HINTS = (
    "explain",
    "teach",
    "tutor",
    "analogy",
    "example",
    "what is",
    "how does",
    "help me understand",
)
RAG_HINTS = (
    "my notes",
    "uploaded",
    "the pdf",
    "the document",
    "according to my",
    "from the file",
    "in the notes",
    "citation",
)
ASSESS_HINTS = ("quiz", "test me", "practice", "questions", "exam questions", "mcq")
MASTERY_HINTS = ("mastery", "how am i doing", "progress", "weak", "strengths", "score")
PLAN_HINTS = ("study plan", "exam in", "schedule", "days until", "timetable", "plan my")
REVISION_HINTS = ("revise", "review", "forgotten", "weak topics", "weak areas")


def _contains(text: str, hints: tuple[str, ...]) -> bool:
    return any(h in text for h in hints)


def route_intent(message: str, has_documents: bool) -> dict[str, Any]:
    text = (message or "").strip().lower()
    tools: list[str] = []
    intent = "tutor"

    if _contains(text, PLAN_HINTS):
        tools.append("planner")
        intent = "planner"
    if _contains(text, MASTERY_HINTS) or _contains(text, ("weak topic", "weak concept")):
        tools.append("mastery")
        intent = "mastery" if intent == "tutor" else intent
    if _contains(text, REVISION_HINTS):
        tools.append("revision")
        intent = "revision" if intent == "tutor" else intent
    if _contains(text, ASSESS_HINTS):
        tools.append("assessment")
        intent = "assessment" if intent == "tutor" else intent
    if has_documents and (
        _contains(text, RAG_HINTS) or "notes" in text or "pdf" in text or "document" in text
    ):
        tools.append("rag")
        if intent == "tutor":
            intent = "rag"
    if _contains(text, TUTOR_HINTS) and "tutor" not in tools and intent in {"tutor", "revision"}:
        tools.append("tutor")

    if not tools:
        if has_documents and len(text.split()) > 3:
            tools = ["rag"]
            intent = "rag"
        else:
            tools = ["tutor"]
            intent = "tutor"

    # Mixed exam + notes + weak topics → compose, do not dump every agent
    if "planner" in tools and ("rag" in tools or "mastery" in tools or "revision" in tools):
        ordered = []
        for name in ("mastery", "rag", "planner", "revision", "assessment", "tutor"):
            if name in tools and name not in ordered:
                ordered.append(name)
        tools = ordered
        intent = "compose"

    days = None
    match = re.search(r"(\d+)\s+days?", text)
    if match:
        days = int(match.group(1))

    return {"intent": intent, "tools": tools, "exam_days": days}


def tutor_agent(message: str, topic: str | None, user_email: str) -> dict[str, Any]:
    from ..advanced_ai import tutor_respond

    return {
        "agent": "tutor",
        **tutor_respond(
            topic=topic or "general",
            concept=None,
            action="explain_simply",
            context=message,
            previous_strategies=[],
            user_email=user_email,
        ),
    }


def rag_agent(message: str, user_email: str) -> dict[str, Any]:
    result = ask_documents(user_email=user_email, question=message)
    return {"agent": "rag", **result}


def assessment_agent(topic: str, user_email: str, difficulty: str = "medium") -> dict[str, Any]:
    from ..advanced_ai import generate_adaptive_quiz
    from ..history import create_session
    from ..mastery import get_mastery_profile

    profile = get_mastery_profile(user_email)
    weak = [c["concept"] for c in (profile.get("weak_concepts") or [])][:5] or [topic]
    quiz = generate_adaptive_quiz(topic, weak, difficulty, user_email=user_email)
    session_id = create_session(
        user_email=user_email,
        topic=topic,
        mode=f"practice_{difficulty}",
        lesson={
            "explanation": f"Adaptive practice focused on: {', '.join(weak)}",
            "key_concepts": weak[:3],
            "quiz": quiz,
        },
    )
    return {
        "agent": "assessment",
        "session_id": session_id,
        "quiz": quiz,
        "focus_concepts": weak,
        "difficulty": difficulty,
    }


def mastery_agent(user_email: str) -> dict[str, Any]:
    from ..ml.predict import predict_profile

    profile = get_mastery_profile(user_email)
    ml = predict_profile(user_email, profile.get("concepts") or [])
    gaps = recommended_next_concepts([c["concept"] for c in (profile.get("weak_concepts") or [])][:5])
    return {
        "agent": "mastery",
        "overall_mastery": profile.get("overall_mastery"),
        "weak_concepts": profile.get("weak_concepts"),
        "critical_concepts": profile.get("critical_concepts"),
        "ml": ml,
        "prerequisite_gaps": gaps[:6],
    }


def planner_agent(
    message: str,
    user_email: str,
    exam_days: int | None,
    weak: list[str],
    retrieved_note: str | None,
) -> dict[str, Any]:
    from ..advanced_ai import generate_study_plan

    exam_name = "Upcoming exam"
    match = re.search(r"([A-Za-z][A-Za-z0-9 +\-]{2,40} exam)", message, flags=re.I)
    if match:
        exam_name = match.group(1)
    topics = weak[:6] or ["core ideas"]
    notes = f" Daily minutes assumed 60. Weak topics: {', '.join(topics)}."
    if retrieved_note:
        notes += " Use uploaded notes where cited."
    if exam_days:
        from datetime import date, timedelta

        exam_date = (date.today() + timedelta(days=exam_days)).isoformat()
    else:
        exam_date = "TBD"
    plan = generate_study_plan(
        exam_name=exam_name,
        exam_date=exam_date,
        daily_minutes=60,
        level="beginner",
        topics=topics,
        user_email=user_email,
    )
    return {"agent": "planner", "notes": notes.strip(), **plan}


def revision_agent(user_email: str, topic: str | None) -> dict[str, Any]:
    from ..advanced_ai import generate_revision_lesson
    from ..history import create_session

    profile = get_mastery_profile(user_email)
    weak = profile.get("weak_concepts") or []
    if not weak and profile.get("concepts"):
        weak = sorted(profile["concepts"], key=lambda c: c.get("mastery_score", 0))[:3]
    concepts = [c["concept"] if isinstance(c, dict) else str(c) for c in weak[:5]]
    topic = topic or ((weak[0].get("topic") if weak and isinstance(weak[0], dict) else None) or "General review")
    if not concepts:
        return {
            "agent": "revision",
            "error": "No weak concepts yet. Complete a quiz first so revision can be personalized.",
        }
    lesson = generate_revision_lesson(topic=topic, weak_concepts=concepts, user_email=user_email)
    session_id = create_session(
        user_email=user_email,
        topic=f"Revision: {topic}",
        mode="study",
        lesson={
            "explanation": lesson["explanation"],
            "key_concepts": lesson.get("key_concepts") or concepts[:3],
            "quiz": lesson["quiz"],
        },
    )
    return {
        "agent": "revision",
        "session_id": session_id,
        "topic": f"Revision: {topic}",
        "explanation": lesson["explanation"],
        "key_concepts": lesson.get("key_concepts") or concepts[:3],
        "quiz": lesson["quiz"],
        "focused_concepts": concepts,
    }


def run_orchestrator(*, message: str, user_email: str, topic: str | None = None) -> dict[str, Any]:
    user_email = (user_email or "").strip().lower()
    docs = list_user_documents(user_email)
    has_documents = any(d.get("status") == "ready" for d in docs)
    decision = route_intent(message, has_documents)
    tools = decision["tools"]
    results: dict[str, Any] = {}
    summary_parts: list[str] = []

    if "mastery" in tools:
        results["mastery"] = mastery_agent(user_email)
        weak_names = [c["concept"] for c in (results["mastery"].get("weak_concepts") or [])][:4]
        if weak_names:
            summary_parts.append("Weak concepts: " + ", ".join(weak_names) + ".")

    if "rag" in tools and has_documents:
        results["rag"] = rag_agent(message, user_email)
        summary_parts.append(results["rag"].get("answer") or "")

    if "planner" in tools:
        weak_names = []
        if "mastery" in results:
            weak_names = [c["concept"] for c in (results["mastery"].get("weak_concepts") or [])]
        note = None
        if results.get("rag") and not results["rag"].get("insufficient"):
            note = results["rag"].get("answer")
        results["planner"] = planner_agent(
            message, user_email, decision.get("exam_days"), weak_names, note
        )
        summary_parts.append("A day-by-day study plan was generated from your current weak topics.")

    if "revision" in tools:
        results["revision"] = revision_agent(user_email, topic)
        if results["revision"].get("explanation"):
            summary_parts.append("A targeted revision lesson is ready.")

    if "assessment" in tools:
        assess_topic = topic or "your current topic"
        if results.get("mastery") and results["mastery"].get("weak_concepts"):
            assess_topic = results["mastery"]["weak_concepts"][0].get("topic") or assess_topic
        results["assessment"] = assessment_agent(assess_topic, user_email)
        summary_parts.append("An adaptive practice quiz was created.")

    if "tutor" in tools or not results:
        results["tutor"] = tutor_agent(message, topic, user_email)
        summary_parts.append(results["tutor"].get("reply") or "")

    mastery_profile = results.get("mastery") or get_mastery_profile(user_email)
    progress = {
        "total_sessions": get_store().count_sessions(user_email),
        "total_quiz_attempts": len(get_store().list_quiz_results(user_email)),
    }
    rec = recommend_next_action(
        mastery=mastery_profile if "weak_concepts" in mastery_profile else get_mastery_profile(user_email),
        progress=progress,
        documents=docs,
        exam_date=None,
        learning_goal=topic,
        ml_predictions=(results.get("mastery") or {}).get("ml", {}).get("predictions") or [],
        prerequisite_gaps=(results.get("mastery") or {}).get("prerequisite_gaps") or [],
    )
    return {
        "intent": decision["intent"],
        "tools_used": tools,
        "routing": decision,
        "summary": " ".join(p for p in summary_parts if p).strip(),
        "recommendation": rec,
        "results": results,
    }
