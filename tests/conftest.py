from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.storage.factory import reset_store_for_tests
from backend.storage.sqlite_store import SQLiteStore


@pytest.fixture()
def store(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    sqlite = SQLiteStore(db)
    reset_store_for_tests(sqlite)
    monkeypatch.setenv("DATABASE_PATH", str(db))
    yield sqlite
    reset_store_for_tests(None)
