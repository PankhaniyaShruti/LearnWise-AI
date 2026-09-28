"""SQLite store for local/demo mode. User rows are always scoped by user_email."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from ..config import DATABASE_PATH

JSON_FIELDS = {
    "sessions": {"key_concepts", "quiz"},
    "quiz_results": {"weak_concepts"},
    "documents": {"metadata"},
    "document_chunks": {"metadata"},
    "usage_events": {"metadata"},
    "learner_predictions": {"features", "metrics"},
}


def _adapt(table: str, data: dict[str, Any]) -> dict[str, Any]:
    fields = JSON_FIELDS.get(table, set())
    out = dict(data)
    for key in fields:
        if key in out and not isinstance(out[key], str):
            out[key] = json.dumps(out[key])
    return out


def _parse_row(table: str, row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in JSON_FIELDS.get(table, set()):
        if key in data and isinstance(data[key], str):
            try:
                data[key] = json.loads(data[key])
            except json.JSONDecodeError:
                pass
    return data


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  session_id   TEXT PRIMARY KEY,
  user_email   TEXT NOT NULL,
  topic        TEXT NOT NULL,
  mode         TEXT NOT NULL,
  explanation  TEXT NOT NULL,
  key_concepts TEXT NOT NULL,
  quiz         TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_email ON sessions (user_email);

CREATE TABLE IF NOT EXISTS quiz_results (
  result_id      TEXT PRIMARY KEY,
  session_id     TEXT NOT NULL,
  user_email     TEXT NOT NULL,
  topic          TEXT NOT NULL,
  score          INTEGER NOT NULL,
  total          INTEGER NOT NULL,
  percentage     INTEGER NOT NULL,
  weak_concepts  TEXT NOT NULL DEFAULT '[]',
  created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_quiz_results_user_email ON quiz_results (user_email);

CREATE TABLE IF NOT EXISTS concept_mastery (
  id                   TEXT PRIMARY KEY,
  user_email           TEXT NOT NULL,
  topic                TEXT NOT NULL DEFAULT '',
  concept              TEXT NOT NULL,
  attempts             INTEGER NOT NULL DEFAULT 0,
  correct              INTEGER NOT NULL DEFAULT 0,
  consecutive_correct  INTEGER NOT NULL DEFAULT 0,
  last_result          INTEGER NOT NULL DEFAULT 0,
  mastery_score        INTEGER NOT NULL DEFAULT 0,
  mastery_label        TEXT NOT NULL DEFAULT 'Needs Attention',
  next_review_at       TEXT,
  created_at           TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at           TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (user_email, concept)
);

CREATE TABLE IF NOT EXISTS documents (
  id           TEXT PRIMARY KEY,
  user_email   TEXT NOT NULL,
  filename     TEXT NOT NULL,
  file_type    TEXT NOT NULL,
  size_bytes   INTEGER NOT NULL,
  status       TEXT NOT NULL DEFAULT 'pending',
  metadata     TEXT NOT NULL DEFAULT '{}',
  error        TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents (user_email);

CREATE TABLE IF NOT EXISTS document_chunks (
  chunk_id     TEXT PRIMARY KEY,
  document_id  TEXT NOT NULL,
  user_email   TEXT NOT NULL,
  chunk_index  INTEGER NOT NULL,
  page_number  INTEGER,
  text         TEXT NOT NULL,
  metadata     TEXT NOT NULL DEFAULT '{}',
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chunks_user ON document_chunks (user_email);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks (document_id);

CREATE TABLE IF NOT EXISTS kg_concepts (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  domain       TEXT NOT NULL DEFAULT 'general',
  description  TEXT NOT NULL DEFAULT '',
  difficulty   REAL NOT NULL DEFAULT 0.5,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kg_relationships (
  id              TEXT PRIMARY KEY,
  source_id       TEXT NOT NULL,
  target_id       TEXT NOT NULL,
  relation        TEXT NOT NULL,
  weight          REAL NOT NULL DEFAULT 1.0,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (source_id, target_id, relation)
);

CREATE TABLE IF NOT EXISTS usage_events (
  id               TEXT PRIMARY KEY,
  request_id       TEXT NOT NULL,
  user_email       TEXT,
  feature          TEXT NOT NULL,
  model            TEXT,
  prompt_name      TEXT,
  prompt_version   TEXT,
  latency_ms       INTEGER,
  input_tokens     INTEGER,
  output_tokens    INTEGER,
  total_tokens     INTEGER,
  success          INTEGER NOT NULL DEFAULT 1,
  error_type       TEXT,
  rag_used         INTEGER NOT NULL DEFAULT 0,
  retrieved_chunks INTEGER NOT NULL DEFAULT 0,
  metadata         TEXT NOT NULL DEFAULT '{}',
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_events (user_email);
CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_events (created_at);

CREATE TABLE IF NOT EXISTS learner_predictions (
  id                   TEXT PRIMARY KEY,
  user_email           TEXT NOT NULL,
  concept              TEXT NOT NULL,
  mastery_probability  REAL NOT NULL,
  predicted_label      TEXT NOT NULL,
  features             TEXT NOT NULL DEFAULT '{}',
  metrics              TEXT NOT NULL DEFAULT '{}',
  created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_pred_user ON learner_predictions (user_email);

CREATE TABLE IF NOT EXISTS prompt_versions (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  version      TEXT NOT NULL,
  description  TEXT NOT NULL DEFAULT '',
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (name, version)
);
"""


class SQLiteStore:
    backend_name = "sqlite"

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or DATABASE_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(SCHEMA)
                conn.commit()
            finally:
                conn.close()

    def _execute(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(sql, params)
                conn.commit()
            finally:
                conn.close()

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            conn = self._connect()
            try:
                return conn.execute(sql, params).fetchall()
            finally:
                conn.close()

    def _query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        rows = self._query(sql, params)
        return rows[0] if rows else None

    def create_session(self, data: dict[str, Any]) -> None:
        row = _adapt("sessions", data)
        self._execute(
            """INSERT INTO sessions
               (session_id, user_email, topic, mode, explanation, key_concepts, quiz)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                row["session_id"],
                row["user_email"],
                row["topic"],
                row["mode"],
                row["explanation"],
                row["key_concepts"],
                row["quiz"],
            ),
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return _parse_row("sessions", self._query_one("SELECT * FROM sessions WHERE session_id = ?", (session_id,)))

    def get_history(self, user_email: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM sessions WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
            (user_email, limit),
        )
        return [_parse_row("sessions", r) for r in rows]  # type: ignore[misc]

    def delete_sessions(self, user_email: str) -> None:
        self._execute("DELETE FROM sessions WHERE user_email = ?", (user_email,))

    def save_quiz_result(self, data: dict[str, Any]) -> None:
        row = _adapt("quiz_results", data)
        self._execute(
            """INSERT INTO quiz_results
               (result_id, session_id, user_email, topic, score, total, percentage, weak_concepts)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["result_id"],
                row["session_id"],
                row["user_email"],
                row["topic"],
                row["score"],
                row["total"],
                row["percentage"],
                row["weak_concepts"],
            ),
        )

    def get_quiz_history(self, user_email: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM quiz_results WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
            (user_email, limit),
        )
        return [_parse_row("quiz_results", r) for r in rows]  # type: ignore[misc]

    def list_quiz_results(self, user_email: str) -> list[dict[str, Any]]:
        rows = self._query("SELECT * FROM quiz_results WHERE user_email = ?", (user_email,))
        return [_parse_row("quiz_results", r) for r in rows]  # type: ignore[misc]

    def delete_quiz_results(self, user_email: str) -> None:
        self._execute("DELETE FROM quiz_results WHERE user_email = ?", (user_email,))

    def list_session_dates(self, user_email: str, limit: int = 100) -> list[str]:
        rows = self._query(
            "SELECT created_at FROM sessions WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
            (user_email, limit),
        )
        return [str(r["created_at"]) for r in rows]

    def count_sessions(self, user_email: str) -> int:
        row = self._query_one("SELECT COUNT(*) AS n FROM sessions WHERE user_email = ?", (user_email,))
        return int(row["n"]) if row else 0

    def get_concept_mastery(self, user_email: str, concept: str) -> dict[str, Any] | None:
        return _parse_row(
            "concept_mastery",
            self._query_one(
                "SELECT * FROM concept_mastery WHERE user_email = ? AND concept = ? LIMIT 1",
                (user_email, concept),
            ),
        )

    def upsert_concept_mastery(self, data: dict[str, Any], existing_id: str | None) -> None:
        if existing_id:
            self._execute(
                """UPDATE concept_mastery SET
                   topic=?, attempts=?, correct=?, consecutive_correct=?, last_result=?,
                   mastery_score=?, mastery_label=?, next_review_at=?, updated_at=?
                   WHERE id=?""",
                (
                    data["topic"],
                    data["attempts"],
                    data["correct"],
                    data["consecutive_correct"],
                    data["last_result"],
                    data["mastery_score"],
                    data["mastery_label"],
                    data.get("next_review_at"),
                    data["updated_at"],
                    existing_id,
                ),
            )
            return
        self._execute(
            """INSERT INTO concept_mastery
               (id, user_email, topic, concept, attempts, correct, consecutive_correct,
                last_result, mastery_score, mastery_label, next_review_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["id"],
                data["user_email"],
                data["topic"],
                data["concept"],
                data["attempts"],
                data["correct"],
                data["consecutive_correct"],
                data["last_result"],
                data["mastery_score"],
                data["mastery_label"],
                data.get("next_review_at"),
                data.get("created_at"),
                data["updated_at"],
            ),
        )

    def list_concept_mastery(self, user_email: str) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM concept_mastery WHERE user_email = ? ORDER BY mastery_score ASC",
            (user_email,),
        )
        return [dict(r) for r in rows]

    def delete_mastery(self, user_email: str) -> None:
        self._execute("DELETE FROM concept_mastery WHERE user_email = ?", (user_email,))

    def create_document(self, data: dict[str, Any]) -> None:
        row = _adapt("documents", data)
        self._execute(
            """INSERT INTO documents
               (id, user_email, filename, file_type, size_bytes, status, metadata, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["id"],
                row["user_email"],
                row["filename"],
                row["file_type"],
                row["size_bytes"],
                row.get("status", "pending"),
                row.get("metadata", "{}"),
                row.get("error"),
            ),
        )

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        return _parse_row("documents", self._query_one("SELECT * FROM documents WHERE id = ?", (document_id,)))

    def list_documents(self, user_email: str) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM documents WHERE user_email = ? ORDER BY created_at DESC",
            (user_email,),
        )
        return [_parse_row("documents", r) for r in rows]  # type: ignore[misc]

    def update_document(self, document_id: str, fields: dict[str, Any]) -> None:
        if not fields:
            return
        adapted = _adapt("documents", fields)
        assignments = ", ".join(f"{k} = ?" for k in adapted)
        values = tuple(adapted.values()) + (document_id,)
        self._execute(f"UPDATE documents SET {assignments} WHERE id = ?", values)

    def delete_document(self, document_id: str) -> None:
        self.delete_chunks(document_id)
        self._execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def replace_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> None:
        self.delete_chunks(document_id)
        for chunk in chunks:
            row = _adapt("document_chunks", chunk)
            self._execute(
                """INSERT INTO document_chunks
                   (chunk_id, document_id, user_email, chunk_index, page_number, text, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["chunk_id"],
                    row["document_id"],
                    row["user_email"],
                    row["chunk_index"],
                    row.get("page_number"),
                    row["text"],
                    row.get("metadata", "{}"),
                ),
            )

    def list_chunks_for_user(
        self, user_email: str, document_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        if document_ids:
            placeholders = ",".join("?" * len(document_ids))
            rows = self._query(
                f"SELECT * FROM document_chunks WHERE user_email = ? AND document_id IN ({placeholders}) ORDER BY chunk_index",
                (user_email, *document_ids),
            )
        else:
            rows = self._query(
                "SELECT * FROM document_chunks WHERE user_email = ? ORDER BY document_id, chunk_index",
                (user_email,),
            )
        return [_parse_row("document_chunks", r) for r in rows]  # type: ignore[misc]

    def delete_chunks(self, document_id: str) -> None:
        self._execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))

    def upsert_kg_concept(self, data: dict[str, Any]) -> None:
        self._execute(
            """INSERT INTO kg_concepts (id, name, domain, description, difficulty)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 domain=excluded.domain,
                 description=excluded.description,
                 difficulty=excluded.difficulty""",
            (
                data["id"],
                data["name"],
                data.get("domain", "general"),
                data.get("description", ""),
                data.get("difficulty", 0.5),
            ),
        )

    def list_kg_concepts(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._query("SELECT * FROM kg_concepts ORDER BY name")]

    def upsert_kg_relationship(self, data: dict[str, Any]) -> None:
        self._execute(
            """INSERT INTO kg_relationships (id, source_id, target_id, relation, weight)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source_id, target_id, relation) DO UPDATE SET weight=excluded.weight""",
            (
                data["id"],
                data["source_id"],
                data["target_id"],
                data["relation"],
                data.get("weight", 1.0),
            ),
        )

    def list_kg_relationships(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._query("SELECT * FROM kg_relationships")]

    def log_event(self, data: dict[str, Any]) -> None:
        row = _adapt("usage_events", data)
        self._execute(
            """INSERT INTO usage_events
               (id, request_id, user_email, feature, model, prompt_name, prompt_version,
                latency_ms, input_tokens, output_tokens, total_tokens, success, error_type,
                rag_used, retrieved_chunks, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["id"],
                row["request_id"],
                row.get("user_email"),
                row["feature"],
                row.get("model"),
                row.get("prompt_name"),
                row.get("prompt_version"),
                row.get("latency_ms"),
                row.get("input_tokens"),
                row.get("output_tokens"),
                row.get("total_tokens"),
                1 if row.get("success", True) else 0,
                row.get("error_type"),
                1 if row.get("rag_used") else 0,
                row.get("retrieved_chunks") or 0,
                row.get("metadata", "{}"),
            ),
        )

    def list_events(self, user_email: str | None, limit: int = 50) -> list[dict[str, Any]]:
        if user_email:
            rows = self._query(
                "SELECT * FROM usage_events WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
                (user_email, limit),
            )
        else:
            rows = self._query(
                "SELECT * FROM usage_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        parsed = []
        for r in rows:
            item = _parse_row("usage_events", r)
            if item:
                item["success"] = bool(item.get("success"))
                item["rag_used"] = bool(item.get("rag_used"))
                parsed.append(item)
        return parsed

    def save_prediction(self, data: dict[str, Any]) -> None:
        row = _adapt("learner_predictions", data)
        self._execute(
            """INSERT INTO learner_predictions
               (id, user_email, concept, mastery_probability, predicted_label, features, metrics)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                row["id"],
                row["user_email"],
                row["concept"],
                row["mastery_probability"],
                row["predicted_label"],
                row.get("features", "{}"),
                row.get("metrics", "{}"),
            ),
        )

    def list_predictions(self, user_email: str) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM learner_predictions WHERE user_email = ? ORDER BY created_at DESC LIMIT 50",
            (user_email,),
        )
        return [_parse_row("learner_predictions", r) for r in rows]  # type: ignore[misc]
