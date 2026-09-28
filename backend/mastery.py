"""Concept mastery engine.

Formula (documented, preserved as the baseline):
  base = (correct / attempts) * 100
  recency_bonus = +5 if last_result == 1 else -5
  streak_bonus = min(consecutive_correct, 3) * 3
  mastery_score = clamp(base + recency_bonus + streak_bonus, 0, 100)

  Labels:
    0–39  Needs Attention
    40–59 Weak
    60–79 Developing
    80–89 Strong
    90–100 Mastered
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .storage import get_store

logger = logging.getLogger(__name__)


def mastery_label(score: int) -> str:
    if score < 40:
        return "Needs Attention"
    if score < 60:
        return "Weak"
    if score < 80:
        return "Developing"
    if score < 90:
        return "Strong"
    return "Mastered"


def compute_score(attempts: int, correct: int, consecutive_correct: int, last_result: int) -> int:
    if attempts <= 0:
        return 0
    base = (correct / attempts) * 100
    recency = 5 if last_result == 1 else -5
    streak = min(max(consecutive_correct, 0), 3) * 3
    return int(max(0, min(100, round(base + recency + streak))))


def days_until_review(score: int) -> int:
    if score < 60:
        return 1
    if score < 80:
        return 2
    if score < 90:
        return 4
    return 7


def update_concept_mastery(
    user_email: str,
    topic: str,
    concept: str,
    was_correct: bool,
) -> dict[str, Any]:
    user_email = (user_email or "").strip().lower()
    concept = (concept or "").strip()
    topic = (topic or "").strip()
    store = get_store()
    row = store.get_concept_mastery(user_email, concept)

    attempts = (row["attempts"] if row else 0) + 1
    correct = (row["correct"] if row else 0) + (1 if was_correct else 0)
    consecutive = ((row["consecutive_correct"] if row else 0) + 1) if was_correct else 0
    last_result = 1 if was_correct else 0
    score = compute_score(attempts, correct, consecutive, last_result)
    label = mastery_label(score)
    now = datetime.now(timezone.utc)
    next_review = (now + timedelta(days=days_until_review(score))).isoformat()

    payload = {
        "user_email": user_email,
        "topic": topic,
        "concept": concept,
        "attempts": attempts,
        "correct": correct,
        "consecutive_correct": consecutive,
        "last_result": last_result,
        "mastery_score": score,
        "mastery_label": label,
        "next_review_at": next_review,
        "updated_at": now.isoformat(),
    }
    if row:
        store.upsert_concept_mastery(payload, row["id"])
        payload["id"] = row["id"]
    else:
        payload["id"] = str(uuid.uuid4())
        payload["created_at"] = now.isoformat()
        store.upsert_concept_mastery(payload, None)
    return payload


def apply_quiz_to_mastery(
    user_email: str,
    topic: str,
    quiz: list[dict],
    answer_map: dict[int, str],
) -> list[dict[str, Any]]:
    updated = []
    for index, question in enumerate(quiz):
        concept = question.get("concept_tested") or f"Concept {index + 1}"
        was_correct = answer_map.get(index) == question.get("correct_answer")
        updated.append(update_concept_mastery(user_email, topic, concept, was_correct))
    return updated


def get_mastery_profile(user_email: str) -> dict[str, Any]:
    user_email = (user_email or "").strip().lower()
    items = get_store().list_concept_mastery(user_email)
    weak = [c for c in items if c["mastery_score"] < 60]
    strong = [c for c in items if c["mastery_score"] >= 80]
    critical = [c for c in items if c["mastery_score"] < 40]
    improving = [c for c in items if c.get("consecutive_correct", 0) >= 2 and c["mastery_score"] < 90]
    now = datetime.now(timezone.utc)
    due = []
    for c in items:
        nr = c.get("next_review_at")
        if not nr:
            due.append(c)
            continue
        try:
            when = datetime.fromisoformat(str(nr).replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when <= now:
                due.append(c)
        except Exception:
            due.append(c)
    overall = round(sum(c["mastery_score"] for c in items) / len(items)) if items else 0
    recommendations = []
    for c in sorted(weak, key=lambda x: x["mastery_score"])[:5]:
        fails = c["attempts"] - c["correct"]
        recommendations.append(
            {
                "concept": c["concept"],
                "topic": c.get("topic"),
                "mastery_score": c["mastery_score"],
                "mastery_label": c["mastery_label"],
                "why": f"You answered {fails} of {c['attempts']} questions on this concept incorrectly.",
                "what_to_do": f"Review how \"{c['concept']}\" fits into {c.get('topic') or 'the topic'}.",
                "next_step": "Take a short targeted practice quiz on this concept.",
            }
        )
    return {
        "overall_mastery": overall,
        "total_concepts": len(items),
        "concepts": items,
        "weak_concepts": weak,
        "strong_concepts": strong,
        "critical_concepts": critical,
        "improving_concepts": improving,
        "due_for_review": due,
        "recommendations": recommendations,
    }


def get_achievements(user_email: str, progress: dict, mastery: dict) -> list[dict[str, Any]]:
    earned = []
    sessions = progress.get("total_sessions", 0)
    quizzes = progress.get("total_quiz_attempts", 0)
    best = progress.get("best_score", 0)
    mastered = len([c for c in mastery.get("concepts", []) if c.get("mastery_score", 0) >= 90])
    checks = [
        (sessions >= 1, "first_lesson", "First Lesson", "Completed your first learning session."),
        (quizzes >= 1, "first_quiz", "First Quiz", "Submitted your first quiz."),
        (quizzes >= 5, "quiz_five", "Quiz Momentum", "Completed 5 quizzes."),
        (best == 100, "perfect_quiz", "Perfect Score", "Scored 100% on a quiz."),
        (mastered >= 3, "master_three", "Concept Master", "Mastered 3 concepts."),
        (mastered >= 10, "master_ten", "Deep Mastery", "Mastered 10 concepts."),
        (progress.get("average_score", 0) >= 80 and quizzes >= 3, "consistent", "Consistent Learner", "Average score 80%+ across quizzes."),
    ]
    for ok, key, title, desc in checks:
        if ok:
            earned.append({"id": key, "title": title, "description": desc})
    return earned
