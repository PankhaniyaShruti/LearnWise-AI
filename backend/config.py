"""Central configuration. Missing keys fail gracefully at call time, not at import."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "learnwise.db")))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(DATA_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ML_ARTIFACT_DIR = Path(os.getenv("ML_ARTIFACT_DIR", str(ROOT_DIR / "backend" / "ml" / "artifacts")))
ML_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

GROQ_API_KEY = (os.getenv("GROQ_API_KEY") or "").strip()
GROQ_BASE_URL = (os.getenv("GROQ_BASE_URL") or "https://api.groq.com/openai/v1").strip()
GROQ_MODEL = (os.getenv("GROQ_MODEL") or "openai/gpt-oss-20b").strip()
GROQ_MODEL_SIMPLE = (os.getenv("GROQ_MODEL_SIMPLE") or GROQ_MODEL).strip()
GROQ_MODEL_COMPLEX = (os.getenv("GROQ_MODEL_COMPLEX") or GROQ_MODEL).strip()
GROQ_MODEL_STRUCTURED = (os.getenv("GROQ_MODEL_STRUCTURED") or GROQ_MODEL).strip()

XAI_API_KEY = (os.getenv("XAI_API_KEY") or "").strip()
XAI_BASE_URL = (os.getenv("XAI_BASE_URL") or "https://api.x.ai/v1").strip()
XAI_MODEL = (os.getenv("XAI_MODEL") or "grok-4.5").strip()
XAI_MODEL_SIMPLE = (os.getenv("XAI_MODEL_SIMPLE") or XAI_MODEL).strip()
XAI_MODEL_COMPLEX = (os.getenv("XAI_MODEL_COMPLEX") or XAI_MODEL).strip()

LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "auto").strip().lower()
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS") or "60")
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES") or "3")

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES") or str(8 * 1024 * 1024))
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt"}
RAG_TOP_K = int(os.getenv("RAG_TOP_K") or "4")
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE") or "0.08")

ADMIN_EMAIL = (os.getenv("ADMIN_EMAIL") or "").strip().lower()


def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def llm_available() -> bool:
    if LLM_PROVIDER == "groq":
        return bool(GROQ_API_KEY)
    if LLM_PROVIDER == "xai":
        return bool(XAI_API_KEY)
    return bool(GROQ_API_KEY or XAI_API_KEY)


def missing_llm_message() -> str:
    return (
        "No LLM provider is configured. Set GROQ_API_KEY (preferred) or XAI_API_KEY. "
        "See .env.example."
    )
