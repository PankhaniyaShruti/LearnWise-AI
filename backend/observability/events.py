from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def log_usage_event(
    *,
    request_id: str,
    user_email: str | None,
    feature: str,
    model: str | None = None,
    prompt_name: str | None = None,
    prompt_version: str | None = None,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    success: bool = True,
    error_type: str | None = None,
    rag_used: bool = False,
    retrieved_chunks: int = 0,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist an observability event. Never stores raw prompts or document text."""
    payload = {
        "id": str(uuid.uuid4()),
        "request_id": request_id,
        "user_email": (user_email or "").strip().lower() or None,
        "feature": feature,
        "model": model,
        "prompt_name": prompt_name,
        "prompt_version": prompt_version,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "success": success,
        "error_type": error_type,
        "rag_used": rag_used,
        "retrieved_chunks": retrieved_chunks,
        "metadata": metadata or {},
    }
    try:
        from ..storage import get_store

        get_store().log_event(payload)
    except Exception as error:
        logger.warning("Failed to persist usage event: %s", error)


def list_usage_events(user_email: str | None, limit: int = 50) -> list[dict[str, Any]]:
    from ..storage import get_store

    return get_store().list_events(user_email, limit=limit)
