"""Prompt registry. Every LLM call should record prompt_name + version."""
from __future__ import annotations

PROMPTS: dict[tuple[str, str], dict[str, str]] = {
    ("learn", "v1"): {
        "description": "Lesson + 3 key concepts + 3 diagnostic quiz questions",
    },
    ("tutor", "v1"): {
        "description": "Single-strategy tutor reply",
    },
    ("tutor", "v2"): {
        "description": "Tutor reply with strategy rotation when learner is stuck",
    },
    ("rag", "v1"): {
        "description": "Grounded answer from retrieved chunks with source ids",
    },
    ("quiz", "v1"): {
        "description": "Adaptive diagnostic quiz generation",
    },
    ("planner", "v1"): {
        "description": "Exam / study plan generation",
    },
    ("orchestrator", "v1"): {
        "description": "Agent routing classification",
    },
    ("revision", "v1"): {
        "description": "Targeted revision lesson from weak concepts",
    },
    ("flashcards", "v1"): {
        "description": "Flashcard generation",
    },
    ("path", "v1"): {
        "description": "Sequential learning path",
    },
}


def prompt_meta(name: str, version: str) -> dict[str, str]:
    return PROMPTS.get((name, version), {"description": name})
