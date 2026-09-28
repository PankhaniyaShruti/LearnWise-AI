-- LearnWise AI v4 — Adaptive Learning Intelligence & Agentic RAG
-- Run in Supabase SQL Editor for production.
--
-- Local/demo mode does NOT need this file: the backend uses SQLite automatically
-- when SUPABASE_URL / SUPABASE_KEY are missing.
--
-- Production: enable RLS and replace the permissive policies below with
-- auth.uid()/email-scoped policies before exposing the project beyond a demo.

CREATE TABLE IF NOT EXISTS public.sessions (
  session_id   TEXT PRIMARY KEY,
  user_email   TEXT NOT NULL,
  topic        TEXT NOT NULL,
  mode         TEXT NOT NULL,
  explanation  TEXT NOT NULL,
  key_concepts JSONB NOT NULL,
  quiz         JSONB NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_email ON public.sessions (user_email);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON public.sessions (created_at DESC);

CREATE TABLE IF NOT EXISTS public.quiz_results (
  result_id      TEXT PRIMARY KEY,
  session_id     TEXT NOT NULL REFERENCES public.sessions (session_id) ON DELETE CASCADE,
  user_email     TEXT NOT NULL,
  topic          TEXT NOT NULL,
  score          INTEGER NOT NULL CHECK (score >= 0),
  total          INTEGER NOT NULL CHECK (total >= 1),
  percentage     INTEGER NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
  weak_concepts  JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quiz_results_user_email ON public.quiz_results (user_email);
CREATE INDEX IF NOT EXISTS idx_quiz_results_session_id ON public.quiz_results (session_id);

CREATE TABLE IF NOT EXISTS public.concept_mastery (
  id                   TEXT PRIMARY KEY,
  user_email           TEXT NOT NULL,
  topic                TEXT NOT NULL DEFAULT '',
  concept              TEXT NOT NULL,
  attempts             INTEGER NOT NULL DEFAULT 0,
  correct              INTEGER NOT NULL DEFAULT 0,
  consecutive_correct  INTEGER NOT NULL DEFAULT 0,
  last_result          INTEGER NOT NULL DEFAULT 0,
  mastery_score        INTEGER NOT NULL DEFAULT 0 CHECK (mastery_score >= 0 AND mastery_score <= 100),
  mastery_label        TEXT NOT NULL DEFAULT 'Needs Attention',
  next_review_at       TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_email, concept)
);
CREATE INDEX IF NOT EXISTS idx_concept_mastery_user ON public.concept_mastery (user_email);
CREATE INDEX IF NOT EXISTS idx_concept_mastery_score ON public.concept_mastery (mastery_score);

CREATE TABLE IF NOT EXISTS public.documents (
  id           TEXT PRIMARY KEY,
  user_email   TEXT NOT NULL,
  filename     TEXT NOT NULL,
  file_type    TEXT NOT NULL,
  size_bytes   INTEGER NOT NULL,
  status       TEXT NOT NULL DEFAULT 'pending',
  metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
  error        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_documents_user ON public.documents (user_email);

CREATE TABLE IF NOT EXISTS public.document_chunks (
  chunk_id     TEXT PRIMARY KEY,
  document_id  TEXT NOT NULL REFERENCES public.documents (id) ON DELETE CASCADE,
  user_email   TEXT NOT NULL,
  chunk_index  INTEGER NOT NULL,
  page_number  INTEGER,
  text         TEXT NOT NULL,
  metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chunks_user ON public.document_chunks (user_email);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON public.document_chunks (document_id);

CREATE TABLE IF NOT EXISTS public.kg_concepts (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  domain       TEXT NOT NULL DEFAULT 'general',
  description  TEXT NOT NULL DEFAULT '',
  difficulty   DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.kg_relationships (
  id         TEXT PRIMARY KEY,
  source_id  TEXT NOT NULL REFERENCES public.kg_concepts (id) ON DELETE CASCADE,
  target_id  TEXT NOT NULL REFERENCES public.kg_concepts (id) ON DELETE CASCADE,
  relation   TEXT NOT NULL,
  weight     DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_id, target_id, relation)
);

CREATE TABLE IF NOT EXISTS public.usage_events (
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
  success          BOOLEAN NOT NULL DEFAULT TRUE,
  error_type       TEXT,
  rag_used         BOOLEAN NOT NULL DEFAULT FALSE,
  retrieved_chunks INTEGER NOT NULL DEFAULT 0,
  metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_user ON public.usage_events (user_email);
CREATE INDEX IF NOT EXISTS idx_usage_created ON public.usage_events (created_at DESC);

CREATE TABLE IF NOT EXISTS public.learner_predictions (
  id                   TEXT PRIMARY KEY,
  user_email           TEXT NOT NULL,
  concept              TEXT NOT NULL,
  mastery_probability  DOUBLE PRECISION NOT NULL,
  predicted_label      TEXT NOT NULL,
  features             JSONB NOT NULL DEFAULT '{}'::jsonb,
  metrics              JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pred_user ON public.learner_predictions (user_email);

CREATE TABLE IF NOT EXISTS public.prompt_versions (
  id           TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  version      TEXT NOT NULL,
  description  TEXT NOT NULL DEFAULT '',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (name, version)
);

ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.concept_mastery ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kg_concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kg_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learner_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prompt_versions ENABLE ROW LEVEL SECURITY;

-- DEMO POLICIES — permissive so the FastAPI service role / anon key can operate.
-- Replace with email-scoped policies before production multi-tenant use.
-- Example production policy:
--   USING (user_email = auth.jwt() ->> 'email')
-- Application code ALSO filters by user_email on every query.

DROP POLICY IF EXISTS "Allow anon all on sessions" ON public.sessions;
DROP POLICY IF EXISTS "Allow anon all on quiz_results" ON public.quiz_results;
DROP POLICY IF EXISTS "Allow anon all on concept_mastery" ON public.concept_mastery;
DROP POLICY IF EXISTS "Allow anon all on documents" ON public.documents;
DROP POLICY IF EXISTS "Allow anon all on document_chunks" ON public.document_chunks;
DROP POLICY IF EXISTS "Allow anon all on kg_concepts" ON public.kg_concepts;
DROP POLICY IF EXISTS "Allow anon all on kg_relationships" ON public.kg_relationships;
DROP POLICY IF EXISTS "Allow anon all on usage_events" ON public.usage_events;
DROP POLICY IF EXISTS "Allow anon all on learner_predictions" ON public.learner_predictions;
DROP POLICY IF EXISTS "Allow anon all on prompt_versions" ON public.prompt_versions;

CREATE POLICY "Allow anon all on sessions" ON public.sessions FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on quiz_results" ON public.quiz_results FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on concept_mastery" ON public.concept_mastery FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on documents" ON public.documents FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on document_chunks" ON public.document_chunks FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on kg_concepts" ON public.kg_concepts FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on kg_relationships" ON public.kg_relationships FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on usage_events" ON public.usage_events FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on learner_predictions" ON public.learner_predictions FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon all on prompt_versions" ON public.prompt_versions FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
