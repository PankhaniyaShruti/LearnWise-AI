"""Supabase-backed store. All queries are scoped by user_email at the application layer."""
from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from ..config import SUPABASE_KEY, SUPABASE_URL


class SupabaseStore:
    backend_name = "supabase"

    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        self.client: Client = create_client(url or SUPABASE_URL, key or SUPABASE_KEY)

    def create_session(self, data: dict[str, Any]) -> None:
        self.client.table("sessions").insert(data).execute()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        res = self.client.table("sessions").select("*").eq("session_id", session_id).execute()
        return res.data[0] if res.data else None

    def get_history(self, user_email: str, limit: int = 20) -> list[dict[str, Any]]:
        res = (
            self.client.table("sessions")
            .select("*")
            .eq("user_email", user_email)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def delete_sessions(self, user_email: str) -> None:
        self.client.table("sessions").delete().eq("user_email", user_email).execute()

    def save_quiz_result(self, data: dict[str, Any]) -> None:
        self.client.table("quiz_results").insert(data).execute()

    def get_quiz_history(self, user_email: str, limit: int = 20) -> list[dict[str, Any]]:
        res = (
            self.client.table("quiz_results")
            .select("*")
            .eq("user_email", user_email)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def list_quiz_results(self, user_email: str) -> list[dict[str, Any]]:
        res = self.client.table("quiz_results").select("*").eq("user_email", user_email).execute()
        return res.data or []

    def delete_quiz_results(self, user_email: str) -> None:
        self.client.table("quiz_results").delete().eq("user_email", user_email).execute()

    def list_session_dates(self, user_email: str, limit: int = 100) -> list[str]:
        res = (
            self.client.table("sessions")
            .select("created_at")
            .eq("user_email", user_email)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [str(r.get("created_at")) for r in (res.data or []) if r.get("created_at")]

    def count_sessions(self, user_email: str) -> int:
        res = self.client.table("sessions").select("session_id").eq("user_email", user_email).execute()
        return len(res.data or [])

    def get_concept_mastery(self, user_email: str, concept: str) -> dict[str, Any] | None:
        res = (
            self.client.table("concept_mastery")
            .select("*")
            .eq("user_email", user_email)
            .eq("concept", concept)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def upsert_concept_mastery(self, data: dict[str, Any], existing_id: str | None) -> None:
        if existing_id:
            self.client.table("concept_mastery").update(data).eq("id", existing_id).execute()
        else:
            self.client.table("concept_mastery").insert(data).execute()

    def list_concept_mastery(self, user_email: str) -> list[dict[str, Any]]:
        res = (
            self.client.table("concept_mastery")
            .select("*")
            .eq("user_email", user_email)
            .order("mastery_score", desc=False)
            .execute()
        )
        return res.data or []

    def delete_mastery(self, user_email: str) -> None:
        self.client.table("concept_mastery").delete().eq("user_email", user_email).execute()

    def create_document(self, data: dict[str, Any]) -> None:
        self.client.table("documents").insert(data).execute()

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        res = self.client.table("documents").select("*").eq("id", document_id).execute()
        return res.data[0] if res.data else None

    def list_documents(self, user_email: str) -> list[dict[str, Any]]:
        res = (
            self.client.table("documents")
            .select("*")
            .eq("user_email", user_email)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    def update_document(self, document_id: str, fields: dict[str, Any]) -> None:
        self.client.table("documents").update(fields).eq("id", document_id).execute()

    def delete_document(self, document_id: str) -> None:
        self.delete_chunks(document_id)
        self.client.table("documents").delete().eq("id", document_id).execute()

    def replace_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> None:
        self.delete_chunks(document_id)
        if chunks:
            self.client.table("document_chunks").insert(chunks).execute()

    def list_chunks_for_user(
        self, user_email: str, document_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        query = self.client.table("document_chunks").select("*").eq("user_email", user_email)
        if document_ids:
            query = query.in_("document_id", document_ids)
        res = query.order("chunk_index").execute()
        return res.data or []

    def delete_chunks(self, document_id: str) -> None:
        self.client.table("document_chunks").delete().eq("document_id", document_id).execute()

    def upsert_kg_concept(self, data: dict[str, Any]) -> None:
        self.client.table("kg_concepts").upsert(data, on_conflict="name").execute()

    def list_kg_concepts(self) -> list[dict[str, Any]]:
        res = self.client.table("kg_concepts").select("*").order("name").execute()
        return res.data or []

    def upsert_kg_relationship(self, data: dict[str, Any]) -> None:
        self.client.table("kg_relationships").upsert(
            data, on_conflict="source_id,target_id,relation"
        ).execute()

    def list_kg_relationships(self) -> list[dict[str, Any]]:
        res = self.client.table("kg_relationships").select("*").execute()
        return res.data or []

    def log_event(self, data: dict[str, Any]) -> None:
        self.client.table("usage_events").insert(data).execute()

    def list_events(self, user_email: str | None, limit: int = 50) -> list[dict[str, Any]]:
        query = self.client.table("usage_events").select("*")
        if user_email:
            query = query.eq("user_email", user_email)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    def save_prediction(self, data: dict[str, Any]) -> None:
        self.client.table("learner_predictions").insert(data).execute()

    def list_predictions(self, user_email: str) -> list[dict[str, Any]]:
        res = (
            self.client.table("learner_predictions")
            .select("*")
            .eq("user_email", user_email)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return res.data or []
