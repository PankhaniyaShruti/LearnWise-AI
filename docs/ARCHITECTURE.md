# LearnWise AI Architecture

LearnWise AI is an adaptive learning platform: generative lessons, diagnostic assessment, mastery tracking, document RAG, a routed agent layer, and LLMOps/MLOps foundations.

## System context

```mermaid
flowchart LR
  Learner[Learner browser] --> UI[React + Vite]
  UI --> API[FastAPI]
  API --> GW[LLM Gateway]
  GW --> Groq[Groq]
  GW --> XAI[xAI fallback]
  API --> Store[Storage]
  Store --> SQLite[SQLite demo]
  Store --> Supa[Supabase Postgres]
  API --> RAG[RAG pipeline]
  API --> ML[Mastery model]
  API --> KG[Knowledge graph]
  API --> Obs[Usage events]
```

## Request path

```mermaid
flowchart TD
  Req[HTTP /api/*] --> Val[Pydantic request models]
  Val --> Own[User ownership checks]
  Own --> Feat{Feature}
  Feat -->|learn/tutor/quiz| GW[LLM Gateway]
  Feat -->|documents/rag| RAG[Extract-chunk-retrieve-generate]
  Feat -->|agent| Orch[Orchestrator]
  Feat -->|quiz submit| Mast[Rule mastery + optional ML]
  GW --> Struct[JSON extract + Pydantic]
  Struct --> Obs[usage_events]
  RAG --> Obs
  Orch --> Tools[Selected agents only]
```

## RAG pipeline

```mermaid
flowchart LR
  U[Upload PDF/TXT] --> V[Type/size validation]
  V --> E[Text extraction]
  E --> C[Chunk + metadata]
  C --> D[(Owned chunks)]
  Q[Question] --> R[TF-IDF retrieve user chunks only]
  D --> R
  R --> S[Untrusted context wrapper]
  S --> L[Grounded LLM JSON]
  L --> Cit[Citations from retrieved ids only]
```

Document text is untrusted. The system prompt forbids following instructions found inside SOURCE blocks. Citations cannot be invented: `used_source_ids` are intersected with retrieved chunk ids.

## Agentic routing

```mermaid
flowchart TD
  M[User message] --> Route[Rule-based planner]
  Route -->|exam + notes + weak| Compose[mastery then rag then planner]
  Route -->|explain| Tutor
  Route -->|uploaded notes| RAG
  Route -->|quiz me| Assessment
  Route -->|how am I doing| Mastery
  Route -->|revise| Revision
```

The orchestrator does not call every agent on every request. Mixed goals compose a short tool list in order.

## Mastery

Two layers:

1. **Rule baseline** (preserved): `score = clamp(accuracy*100 + recency ±5 + streak*3, 0, 100)`.
2. **ML layer**: logistic regression on synthetic bootstrap features (`accuracy`, attempts, recency, streak, difficulty, time gap, rule score). Metrics are stored with an explicit synthetic disclaimer.

The knowledge graph supplies prerequisite gaps (e.g. weak Logistic Regression → Probability / Gradient Descent).

## LLM gateway

All model calls go through `backend/llm/gateway.py`:

- Provider auto-select (Groq, then xAI)
- Task routing (`simple`, `structured`, `complex`, `rag`)
- Timeouts and retries
- Structured output parse + Pydantic
- Prompt name + version
- Token / latency / success events (no raw prompts, no document text)

## Storage

| Mode | When | Backend |
|------|------|---------|
| Local/demo | `SUPABASE_URL` unset | SQLite in `data/learnwise.db` |
| Production | Supabase env set | Postgres via Supabase client + `database/schema.sql` |

Every query is scoped by `user_email`. One learner cannot read another learner's sessions, documents, chunks, or events.
