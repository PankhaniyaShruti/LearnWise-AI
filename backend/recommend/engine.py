"""Next-best-learning-action engine.

Uses learner mastery, prerequisite gaps, documents, exam timing,
and ML predictions to recommend the next learning action.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


WEAK_LABELS = {"Needs Attention", "Weak"}


def _days_until(date_str: str | None) -> int | None:
    if not date_str:
        return None

    try:
        when = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))

        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)

        delta = when - datetime.now(timezone.utc)
        return max(0, delta.days)

    except (TypeError, ValueError, OverflowError):
        return None


def _concept_name(item: dict[str, Any]) -> str | None:
    value = item.get("concept") or item.get("name")
    return str(value).strip() if value else None


def _mastery_score(item: dict[str, Any]) -> float:
    try:
        return float(item.get("mastery_score", 100))
    except (TypeError, ValueError):
        return 100.0


def _lowest_mastery(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [item for item in items if _concept_name(item)]
    return min(valid, key=_mastery_score) if valid else None


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
    concepts = mastery.get("concepts") or []

    overall = mastery.get("overall_mastery") or 0

    ready_docs = [
        doc for doc in documents
        if doc.get("status") == "ready"
    ]

    days = _days_until(exam_date)

    ml_weak = [
        prediction
        for prediction in ml_predictions
        if prediction.get("predicted_label") in WEAK_LABELS
        and _concept_name(prediction)
    ]

    # Build a lookup of ML-flagged concept names.
    ml_weak_names = {
        _concept_name(prediction).casefold()
        for prediction in ml_weak
        if _concept_name(prediction)
    }

    # Prioritize actual critical and weak mastery signals.
    critical_focus = _lowest_mastery(critical)
    weak_focus = _lowest_mastery(weak)

    # If mastery lists do not identify a weak concept,
    # use ML predictions to identify the focus.
    ml_focus = None

    if ml_weak_names:
        matching_concepts = [
            concept
            for concept in concepts
            if _concept_name(concept)
            and _concept_name(concept).casefold() in ml_weak_names
        ]

        ml_focus = (
            matching_concepts[0]
            if matching_concepts
            else ml_weak[0]
        )

    # Select focus using available evidence.
    focus = (
        critical_focus
        or weak_focus
        or ml_focus
        or _lowest_mastery(due)
        or _lowest_mastery(concepts)
    )

    prereq = next(
        (
            gap for gap in prerequisite_gaps
            if gap.get("name")
        ),
        None,
    )

    focus_name = _concept_name(focus) if focus else None
    prereq_name = prereq.get("name") if prereq else None

    if not mastery.get("total_concepts"):

        action = (
            "Start a short lesson on your goal topic, "
            "then take the 3-question diagnostic."
        )

        why = (
            "There is no mastery history yet, so a diagnostic "
            "lesson is the highest-signal next step."
        )

        steps = [
            "Pick one concrete topic (for example Logistic Regression).",
            "Generate a Simple or Study mode lesson.",
            "Complete the quiz so concept scores can be tracked.",
        ]

        kind = "onboard"

    elif prereq and focus_name:

        action = (
            f"Revise prerequisite “{prereq_name}” for 10 minutes, "
            f"then retry “{focus_name}” with 3 medium questions."
        )

        why = (
            f"You need to strengthen {focus_name}, and the "
            f"knowledge graph flags {prereq_name} as a prerequisite gap."
        )

        steps = [
            f"Open a revision lesson on {prereq_name}.",
            "Work 3 medium practice questions.",
            f"Return to {focus_name} and check whether the error pattern changes.",
        ]

        kind = "prerequisite"

    elif days is not None and days <= 14 and (weak_focus or ml_focus):

        concept = focus_name or learning_goal or "your current topic"

        action = (
            f"Exam-focused drill: 15 minutes on {concept}, "
            f"then a medium adaptive quiz. {days} day(s) remain."
        )

        why = (
            "A near-term exam and a weak mastery or ML signal "
            "make focused practice relevant."
        )

        steps = [
            "Generate an exam-mode study plan for the remaining days.",
            f"Prioritize {concept} in today's block.",
            "Use uploaded notes in Documents if you have them.",
        ]

        kind = "exam"

    elif critical_focus:

        concept = _concept_name(critical_focus)

        action = (
            f"Revise {concept} for 10 minutes → "
            "take 3 easy questions → review mistakes."
        )

        why = (
            f"{concept} is labelled Needs Attention "
            "from your actual quiz outcomes."
        )

        steps = [
            "Use Revise My Weak Areas.",
            "Ask the tutor for an analogy if the first explanation does not land.",
            "Stop after the 3-question check and update mastery.",
        ]

        kind = "critical"

    elif ready_docs and (weak_focus or ml_weak):

        concept = focus_name or learning_goal or "your current topic"

        action = (
            f"Ask your notes about {concept}, "
            "then take 3 medium questions on that idea."
        )

        why = (
            "You have processed documents and a weak concept — "
            "grounded retrieval plus a short check beats rereading."
        )

        steps = [
            f"In Documents, ask: “Explain {concept} using my notes.”",
            "Read the cited pages only.",
            "Run Adaptive Practice (medium).",
        ]

        kind = "rag_practice"

    elif due:

        concept = _concept_name(_lowest_mastery(due) or {})

        action = (
            f"Spaced review: 8 minutes on {concept}, "
            "then 3 mixed questions."
        )

        why = "This concept is due for review based on its mastery schedule."

        steps = [
            "Open the original lesson or flashcards.",
            "Answer 3 questions without notes first.",
            "Mark remaining holes for tomorrow.",
        ]

        kind = "spaced"

    elif overall >= 80:

        action = (
            "Stretch: take a hard adaptive quiz "
            "on a related advanced concept."
        )

        why = (
            "Overall mastery is strong, so the next gain "
            "comes from harder retrieval practice."
        )

        steps = [
            "Use Adaptive: Hard.",
            "Add a learning-path step one level above your current topic.",
        ]

        kind = "stretch"

    else:

        concept = focus_name or learning_goal or "your current topic"

        action = (
            f"Revise {concept} for 10 minutes → "
            "take 3 medium questions → review mistakes."
        )

        why = (
            "Recent performance or ML predictions indicate "
            "that a short revise-then-test loop may help."
        )

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
        "focus_concept": focus_name,
        "prerequisite": prereq_name,
        "exam_days_remaining": days,
        "documents_available": len(ready_docs),
        "overall_mastery": overall,
        "goal": learning_goal,
    }