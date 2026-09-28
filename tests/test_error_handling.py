from backend.llm.gateway import extract_json
from backend.models import LearnResponse
from pydantic import ValidationError
import pytest


def test_extract_json_from_fences():
    raw = '```json\n{"a": 1}\n```'
    assert extract_json(raw) == {"a": 1}


def test_extract_json_strips_think():
    raw = '<think>nope</think>{"ok": true}'
    assert extract_json(raw) == {"ok": True}


def test_malformed_json_raises():
    with pytest.raises(ValueError):
        extract_json("not json at all")


def test_incomplete_learn_response_rejected():
    with pytest.raises(ValidationError):
        LearnResponse(explanation="x", key_concepts=["a"], quiz=[])
