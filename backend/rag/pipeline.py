from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..config import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_BYTES, RAG_MIN_SCORE, RAG_TOP_K, UPLOAD_DIR
from ..llm.gateway import complete
from ..storage import get_store
from .chunking import chunk_pages
from .extraction import ExtractionError, extract_pages
from .index import retrieve_chunks
from .security import RAG_SYSTEM_PROMPT, wrap_untrusted_context

logger = logging.getLogger(__name__)


class RagAnswer(BaseModel):
    answer: str = Field(..., min_length=1)
    insufficient: bool = False
    used_source_ids: list[str] = Field(default_factory=list)


def _safe_filename(name: str) -> str:
    base = Path(name or "upload").name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "upload"
    return base[:180]


def _user_dir(user_email: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", (user_email or "guest").lower())[:80]
    path = UPLOAD_DIR / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def process_upload(
    *,
    user_email: str,
    filename: str,
    data: bytes,
    content_type: str | None = None,
) -> dict[str, Any]:
    user_email = (user_email or "").strip().lower()
    filename = _safe_filename(filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError("Only PDF and TXT files are supported.")
    if not data:
        raise ValueError("Empty file.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds the {MAX_UPLOAD_BYTES} byte limit.")

    document_id = str(uuid.uuid4())
    store = get_store()
    store.create_document(
        {
            "id": document_id,
            "user_email": user_email,
            "filename": filename,
            "file_type": suffix.lstrip("."),
            "size_bytes": len(data),
            "status": "processing",
            "metadata": {"content_type": content_type or ""},
            "error": None,
        }
    )
    try:
        dest = _user_dir(user_email) / f"{document_id}{suffix}"
        dest.write_bytes(data)
        pages = extract_pages(filename, data)
        chunks = chunk_pages(pages, document_id=document_id, user_email=user_email, filename=filename)
        store.replace_chunks(document_id, chunks)
        metadata = {
            "content_type": content_type or "",
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "stored_path": str(dest.name),
        }
        store.update_document(
            document_id,
            {"status": "ready", "metadata": metadata, "error": None},
        )
        doc = store.get_document(document_id) or {}
        return {**doc, "chunk_count": len(chunks)}
    except ExtractionError as error:
        store.update_document(document_id, {"status": "failed", "error": str(error)})
        raise ValueError(str(error)) from error
    except Exception as error:
        store.update_document(document_id, {"status": "failed", "error": "Document processing failed."})
        logger.exception("Document processing failed")
        raise ValueError("Document processing failed.") from error


def list_user_documents(user_email: str) -> list[dict[str, Any]]:
    return get_store().list_documents((user_email or "").strip().lower())


def get_owned_document(user_email: str, document_id: str) -> dict[str, Any] | None:
    doc = get_store().get_document(document_id)
    if not doc:
        return None
    if (doc.get("user_email") or "").strip().lower() != (user_email or "").strip().lower():
        return None
    return doc


def delete_owned_document(user_email: str, document_id: str) -> bool:
    doc = get_owned_document(user_email, document_id)
    if not doc:
        return False
    get_store().delete_document(document_id)
    suffix = f".{doc.get('file_type')}" if doc.get("file_type") else ""
    path = _user_dir(user_email) / f"{document_id}{suffix}"
    if path.exists():
        path.unlink()
    return True


def _attach_filenames(user_email: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs = {d["id"]: d for d in list_user_documents(user_email)}
    attached = []
    for chunk in chunks:
        item = dict(chunk)
        doc = docs.get(chunk.get("document_id"))
        filename = (chunk.get("metadata") or {}).get("filename") if isinstance(chunk.get("metadata"), dict) else None
        item["filename"] = filename or (doc.get("filename") if doc else "document")
        attached.append(item)
    return attached


def retrieve_for_user(
    *,
    user_email: str,
    question: str,
    document_ids: list[str] | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    user_email = (user_email or "").strip().lower()
    owned_ids = None
    if document_ids:
        owned = []
        for did in document_ids:
            if get_owned_document(user_email, did):
                owned.append(did)
        owned_ids = owned
        if not owned_ids:
            return []
    chunks = get_store().list_chunks_for_user(user_email, owned_ids)
    chunks = _attach_filenames(user_email, chunks)
    return retrieve_chunks(question, chunks, top_k=top_k or RAG_TOP_K, min_score=RAG_MIN_SCORE)


def question_needs_documents(question: str, has_documents: bool) -> bool:
    if not has_documents:
        return False
    q = (question or "").lower()
    hints = (
        "my notes",
        "the pdf",
        "the document",
        "uploaded",
        "according to",
        "in the notes",
        "from the file",
        "citation",
        "source",
        "page",
    )
    return any(h in q for h in hints) or True  # if user is in RAG chat, always try retrieval


def ask_documents(
    *,
    user_email: str,
    question: str,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    retrieved = retrieve_for_user(user_email=user_email, question=question, document_ids=document_ids)
    if not retrieved:
        return {
            "answer": (
                "The uploaded material does not contain enough information to answer this question. "
                "Try a more specific question, or upload a document that covers this topic."
            ),
            "insufficient": True,
            "citations": [],
            "retrieved": [],
            "rag_used": True,
        }

    context = wrap_untrusted_context(retrieved)
    user_prompt = (
        f"{context}\n\nQUESTION:\n{question}\n\n"
        "Answer using only the SOURCE blocks. If they are not enough, set insufficient=true."
    )
    _result, parsed = complete(
        [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        feature="rag_ask",
        prompt_name="rag",
        prompt_version="v1",
        user_email=user_email,
        task="rag",
        temperature=0.1,
        max_tokens=1200,
        schema=RagAnswer,
        rag_used=True,
        retrieved_chunks=len(retrieved),
    )
    allowed = {c["chunk_id"] for c in retrieved}
    used_ids = [cid for cid in parsed.used_source_ids if cid in allowed]
    if not used_ids:
        used_ids = [c["chunk_id"] for c in retrieved[:2]]
        if parsed.insufficient:
            used_ids = []
    citations = []
    by_id = {c["chunk_id"]: c for c in retrieved}
    for cid in used_ids:
        chunk = by_id.get(cid)
        if not chunk:
            continue
        citations.append(
            {
                "chunk_id": cid,
                "filename": chunk.get("filename"),
                "page_number": chunk.get("page_number"),
                "chunk_index": chunk.get("chunk_index"),
                "score": chunk.get("retrieval_score"),
                "snippet": (chunk.get("text") or "")[:280],
            }
        )
    answer = parsed.answer
    if parsed.insufficient and not citations:
        answer = (
            parsed.answer
            or "The uploaded material does not contain enough information to answer this question."
        )
    return {
        "answer": answer,
        "insufficient": parsed.insufficient,
        "citations": citations,
        "retrieved": [
            {
                "chunk_id": c["chunk_id"],
                "filename": c.get("filename"),
                "page_number": c.get("page_number"),
                "score": c.get("retrieval_score"),
            }
            for c in retrieved
        ],
        "rag_used": True,
    }
