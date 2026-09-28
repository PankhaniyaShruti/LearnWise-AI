"""Offline RAG evaluation helpers. Scores are computed, never fabricated."""
from __future__ import annotations

import json
from pathlib import Path

from backend.rag.index import retrieve_chunks

EVAL_PATH = Path(__file__).resolve().parent / "rag_eval_set.json"


def load_eval_set() -> list[dict]:
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))


def evaluate_retrieval(dataset: list[dict] | None = None) -> dict:
    dataset = dataset or load_eval_set()
    hits = 0
    mrr_total = 0.0
    for row in dataset:
        ranked = retrieve_chunks(row["question"], row["chunks"], top_k=3, min_score=0.0)
        ids = [c["chunk_id"] for c in ranked]
        expected = set(row["relevant_chunk_ids"])
        if ids and ids[0] in expected:
            hits += 1
        rank = next((i + 1 for i, cid in enumerate(ids) if cid in expected), None)
        mrr_total += (1 / rank) if rank else 0.0
    n = max(len(dataset), 1)
    return {
        "n": len(dataset),
        "hit_at_1": round(hits / n, 4),
        "mrr": round(mrr_total / n, 4),
        "note": "Computed on the bundled evaluation set. Not a production benchmark.",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_retrieval(), indent=2))
