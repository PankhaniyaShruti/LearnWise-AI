from backend.agents.orchestrator import route_intent


def test_routes_tutor():
    d = route_intent("Explain overfitting with an analogy", has_documents=False)
    assert "tutor" in d["tools"] or d["intent"] == "tutor"


def test_routes_rag_when_notes_mentioned():
    d = route_intent("Using my uploaded notes, what is overfitting?", has_documents=True)
    assert "rag" in d["tools"]


def test_does_not_call_rag_without_docs():
    d = route_intent("Using my uploaded notes, what is overfitting?", has_documents=False)
    assert "rag" not in d["tools"]


def test_compose_exam_and_weak_and_notes():
    d = route_intent(
        "I have an ML exam in 10 days. I uploaded my notes. Make a study plan and teach me my weak topics.",
        has_documents=True,
    )
    assert d["intent"] == "compose"
    assert "planner" in d["tools"]
    assert "rag" in d["tools"]
    assert d["tools"][0] in {"mastery", "rag", "planner", "revision"}
    assert d["exam_days"] == 10
    # Does not blindly include every agent
    assert set(d["tools"]) <= {"mastery", "rag", "planner", "revision", "assessment", "tutor"}


def test_assessment_route():
    d = route_intent("Give me practice questions on precision", has_documents=False)
    assert "assessment" in d["tools"]
