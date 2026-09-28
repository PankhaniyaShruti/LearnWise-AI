"""Next-best-learning-action engine. Uses real learner state, graph, docs, and ML labels."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _days_until(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        when = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        delta = when - datetime.now(timezone.utc)
        return max(0, delta.days)
    except Exception:
        return None


def recommend_next_action(
    *,
    mastery: dict[str, Any],
    progress: dict[str, Any],
    documents: list[dict[str, Any]] | None = None,
    exam_date: str | None = None,
    learning_goal: str | None = None,
    ml_predictions: list[dict[str, Any]] | None = None,
    prerequisite_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    documents = documents or []
    ml_predictions = ml_predictions or []
    prerequisite_gaps = prerequisite_gaps or []
    weak = mastery.get("weak_concepts") or []
    critical = mastery.get("critical_concepts") or []
    due = mastery.get("due_for_review") or []
    overall = mastery.get("overall_mastery") or 0
    ready_docs = [d for d in documents if d.get("status") == "ready"]
    days = _days_until(exam_date)

    focus = None
    if critical:
        focus = critical[0]
    elif weak:
        focus = weak[0]
    elif due:
        focus = due[0]
    elif mastery.get("concepts"):
        focus = sorted(mastery["concepts"], key=lambda c: c.get("mastery_score", 0))[0]

    prereq = prerequisite_gaps[0] if prerequisite_gaps else None
    ml_weak = [
        p
        for p in ml_predictions
        if p.get("predicted_label") in {"Needs Attention", "Weak"}
    ]

    if not mastery.get("total_concepts"):
        action = "Start a short lesson on your goal topic, then take the 3-question diagnostic."
        why = "There is no mastery history yet, so a diagnostic lesson is the highest-signal next step."
        steps = [
            "Pick one concrete topic (for example Logistic Regression).",
            "Generate a Simple or Study mode lesson.",
            "Complete the quiz so concept scores can be tracked.",
        ]
        kind = "onboard"
    elif prereq and focus:
        action = (
            f"Revise prerequisite “{prereq.get('name')}” for 10 minutes, "
            f"then retry “{focus.get('concept')}” with 3 medium questions."
        )
        why = (
            f"You are weak in {focus.get('concept')}, and the knowledge graph "
            f"flags {prereq.get('name')} as a prerequisite gap."
        )
        steps = [
            f"Open a revision lesson on {prereq.get('name')}.",
            "Work 3 medium practice questions.",
            f"Return to {focus.get('concept')} and check whether the error pattern changes.",
        ]
        kind = "prerequisite"
    elif critical:
        concept = critical[0]["concept"]
        action = f"Revise {concept} for 10 minutes → take 3 easy questions → review mistakes."
        why = f"{concept} is labelled Needs Attention from your actual quiz outcomes."
        steps = [
            "Use Revise My Weak Areas.",
            "Ask the tutor for an analogy if the first explanation does not land.",
            "Stop after the 3-question check and update mastery.",
        ]
        kind = "critical"
    elif days is not None and days <= 14 and weak:
        concept = weak[0]["concept"]
        action = (
            f"Exam-focused drill: 15 minutes on {concept}, then a medium adaptive quiz. "
            f"{days} day(s) remain."
        )
        why = "A near-term exam plus weak concepts makes short mixed practice the best use of time."
        steps = [
            "Generate an exam-mode study plan for the remaining days.",
            f"Prioritize {concept} in today's block.",
            "Use uploaded notes in Documents if you have them.",
        ]
        kind = "exam"
    elif ready_docs and (weak or ml_weak):
        concept = (weak[0]["concept"] if weak else ml_weak[0].get("concept"))
        action = f"Ask your notes about {concept}, then take 3 medium questions on that idea."
        why = "You have processed documents and a weak concept — grounded retrieval plus a short check beats rereading."
        steps = [
            f"In Documents, ask: “Explain {concept} using my notes.”",
            "Read the cited pages only.",
            "Run Adaptive Practice (medium).",
        ]
        kind = "rag_practice"
    elif due:
        concept = due[0]["concept"]
        action = f"Spaced review: 8 minutes on {concept}, then 3 mixed questions."
        why = "This concept is due for review based on its mastery schedule."
        steps = [
            "Open the original lesson or flashcards.",
            "Answer 3 questions without notes first.",
            "Mark remaining holes for tomorrow.",
        ]
        kind = "spaced"
    elif overall >= 80:
        action = "Stretch: take a hard adaptive quiz on a related advanced concept."
        why = "Overall mastery is strong, so the next gain comes from harder retrieval practice."
        steps = [
            "Use Adaptive: Hard.",
            "Add a learning-path step one level above your current topic.",
        ]
        kind = "stretch"
    else:
        concept = focus["concept"] if focus else (learning_goal or "your current topic")
        action = f"Revise {concept} for 10 minutes → take 3 medium questions → review mistakes."
        why = "Recent performance still has gaps; a short revise-then-test loop is the default high-value action."
        steps = [
            "Revise the concept with the tutor or a targeted lesson.",
            "Submit an adaptive quiz.",
            "Check the updated mastery bar before stopping.",
        ]
        kind = "default"

    return {
        "action": action,
        "why": why,
        "steps": steps,
        "kind": kind,
        "focus_concept": (focus or {}).get("concept"),
        "prerequisite": (prereq or {}).get("name"),
        "exam_days_remaining": days,
        "documents_available": len(ready_docs),
        "overall_mastery": overall,
        "goal": learning_goal,
    }
