from __future__ import annotations

import logging
from typing import Any

from ..config import supabase_configured

logger = logging.getLogger(__name__)

_store: Any | None = None


def get_store():
    global _store
    if _store is not None:
        return _store
    if supabase_configured():
        from .supabase_store import SupabaseStore

        logger.info("Using Supabase storage backend.")
        _store = SupabaseStore()
    else:
        from .sqlite_store import SQLiteStore

        logger.info("Supabase not configured — using local SQLite demo store.")
        _store = SQLiteStore()
    return _store


def reset_store_for_tests(store=None) -> None:
    global _store
    _store = store
