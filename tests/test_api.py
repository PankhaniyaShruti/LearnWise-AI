from fastapi.testclient import TestClient

from backend.app import app
from backend.history import create_session
from backend.storage.factory import reset_store_for_tests
from backend.storage.sqlite_store import SQLiteStore


def client_with_store(tmp_path):
    store = SQLiteStore(tmp_path / "api.db")
    reset_store_for_tests(store)
    return TestClient(app), store


def test_health(tmp_path):
    client, _ = client_with_store(tmp_path)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert "storage" in body


def test_quiz_submit_and_ownership(tmp_path):
    client, store = client_with_store(tmp_path)
    quiz = [
        {
            "question": "Q1",
            "options": ["a", "b", "c", "d"],
            "correct_answer": "a",
            "concept_tested": "Precision",
        },
        {
            "question": "Q2",
            "options": ["a", "b", "c", "d"],
            "correct_answer": "b",
            "concept_tested": "Recall",
        },
        {
            "question": "Q3",
            "options": ["a", "b", "c", "d"],
            "correct_answer": "c",
            "concept_tested": "F1",
        },
    ]
    sid = create_session(
        "alice@test.com",
        "ML",
        "simple",
        {"explanation": "exp", "key_concepts": ["Precision", "Recall", "F1"], "quiz": quiz},
    )
    forbidden = client.post(
        "/api/quiz/submit",
        json={
            "session_id": sid,
            "user_email": "bob@test.com",
            "answers": [
                {"question_index": 0, "selected_answer": "a"},
                {"question_index": 1, "selected_answer": "a"},
                {"question_index": 2, "selected_answer": "c"},
            ],
        },
    )
    assert forbidden.status_code == 403
    ok = client.post(
        "/api/quiz/submit",
        json={
            "session_id": sid,
            "user_email": "alice@test.com",
            "answers": [
                {"question_index": 0, "selected_answer": "a"},
                {"question_index": 1, "selected_answer": "a"},
                {"question_index": 2, "selected_answer": "c"},
            ],
        },
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["score"] == 2
    assert body["total"] == 3
    assert "Recall" in body["weak_concepts"]
    hist = client.get("/api/history", params={"email": "alice@test.com"})
    assert hist.status_code == 200
    assert hist.json()["total"] == 1
    other = client.get("/api/history", params={"email": "bob@test.com"})
    assert other.json()["total"] == 0


def test_document_upload_and_isolation(tmp_path):
    client, _ = client_with_store(tmp_path)
    res = client.post(
        "/api/documents",
        data={"user_email": "alice@test.com"},
        files={"file": ("notes.txt", b"Precision is TP / (TP + FP).", "text/plain")},
    )
    assert res.status_code == 200
    doc_id = res.json()["id"]
    listed = client.get("/api/documents", params={"email": "bob@test.com"})
    assert listed.json()["items"] == []
    missing = client.get(f"/api/documents/{doc_id}", params={"email": "bob@test.com"})
    assert missing.status_code == 404
    owned = client.get(f"/api/documents/{doc_id}", params={"email": "alice@test.com"})
    assert owned.status_code == 200


def test_learn_validation_error(tmp_path):
    client, _ = client_with_store(tmp_path)
    res = client.post("/api/learn", json={"topic": "", "mode": "simple"})
    assert res.status_code == 422


def test_knowledge_graph(tmp_path):
    client, _ = client_with_store(tmp_path)
    from backend.knowledge.graph import ensure_seeded

    ensure_seeded()
    res = client.get("/api/knowledge-graph")
    assert res.status_code == 200
    body = res.json()
    assert len(body["concepts"]) >= 10
    assert len(body["relationships"]) >= 10


def test_observability_scoped(tmp_path):
    client, store = client_with_store(tmp_path)
    store.log_event(
        {
            "id": "e1",
            "request_id": "r1",
            "user_email": "alice@test.com",
            "feature": "learn",
            "model": "test",
            "prompt_name": "learn",
            "prompt_version": "v1",
            "latency_ms": 10,
            "success": True,
            "rag_used": False,
            "retrieved_chunks": 0,
            "metadata": {},
        }
    )
    mine = client.get("/api/observability", params={"email": "alice@test.com"})
    assert mine.status_code == 200
    assert mine.json()["total"] == 1
    other = client.get("/api/observability", params={"email": "bob@test.com"})
    assert other.json()["total"] == 0
