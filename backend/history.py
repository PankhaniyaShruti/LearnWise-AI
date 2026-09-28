import logging
import uuid
from datetime import date, timedelta
from typing import Any

from .storage import get_store

logger = logging.getLogger(__name__)


def create_session(user_email: str, topic: str, mode: str, lesson: dict[str, Any]) -> str:
    session_id = str(uuid.uuid4())
    get_store().create_session(
        {
            "session_id": session_id,
            "user_email": user_email or "guest@learnwise.com",
            "topic": topic,
            "mode": mode,
            "explanation": lesson["explanation"],
            "key_concepts": lesson["key_concepts"],
            "quiz": lesson["quiz"],
        }
    )
    logger.info("Created learning session: %s for %s", session_id, user_email)
    return session_id


def get_session(session_id: str) -> dict[str, Any] | None:
    return get_store().get_session(session_id)


def get_history(user_email: str, limit: int = 20) -> list[dict[str, Any]]:
    return get_store().get_history(user_email, limit)


def save_quiz_result(
    user_email: str,
    session_id: str,
    score: int,
    total: int,
    percentage: int,
    weak_concepts: list[str],
) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise ValueError("Learning session not found.")
    result_id = str(uuid.uuid4())
    data = {
        "result_id": result_id,
        "session_id": session_id,
        "user_email": user_email or "guest@learnwise.com",
        "topic": session["topic"],
        "score": score,
        "total": total,
        "percentage": percentage,
        "weak_concepts": weak_concepts,
    }
    get_store().save_quiz_result(data)
    logger.info("Saved quiz result for session %s: %s/%s", session_id, score, total)
    return data


def get_quiz_history(user_email: str, limit: int = 20) -> list[dict[str, Any]]:
    return get_store().get_quiz_history(user_email, limit)


def get_progress(user_email: str) -> dict[str, Any]:
    store = get_store()
    total_sessions = store.count_sessions(user_email)
    quizzes = store.list_quiz_results(user_email)
    total_quiz_attempts = len(quizzes)
    if total_quiz_attempts > 0:
        average_score = round(sum(q["percentage"] for q in quizzes) / total_quiz_attempts)
        best_score = max(q["percentage"] for q in quizzes)
    else:
        average_score = 0
        best_score = 0
    weak_counter: dict[str, int] = {}
    for q in quizzes:
        for concept in q.get("weak_concepts") or []:
            weak_counter[concept] = weak_counter.get(concept, 0) + 1
    weak_concepts = [
        concept
        for concept, _ in sorted(weak_counter.items(), key=lambda item: item[1], reverse=True)
    ][:5]
    streak = 0
    try:
        dates = set()
        for ca in store.list_session_dates(user_email, limit=100):
            dates.add(str(ca)[:10])
        if dates:
            day = date.today()
            while day.isoformat() in dates:
                streak += 1
                day = day - timedelta(days=1)
    except Exception:
        streak = 0
    return {
        "total_sessions": total_sessions,
        "total_quiz_attempts": total_quiz_attempts,
        "average_score": average_score,
        "best_score": best_score,
        "weak_concepts": weak_concepts,
        "streak_days": streak,
    }


def clear_history(user_email: str) -> None:
    store = get_store()
    store.delete_quiz_results(user_email)
    store.delete_sessions(user_email)
    store.delete_mastery(user_email)
    logger.info("Learning history cleared for user: %s", user_email)
