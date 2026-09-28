"""In-process TF-IDF retrieval. Rebuilt from a user's own chunks — never mixed across users."""
from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def retrieve_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    top_k: int = 4,
    min_score: float = 0.08,
) -> list[dict[str, Any]]:
    if not query.strip() or not chunks:
        return []
    corpus = [(c.get("text") or "").strip() for c in chunks]
    if not any(corpus):
        return []
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    try:
        matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query])
    except ValueError:
        return []
    scores = cosine_similarity(query_vec, matrix).flatten()
    ranked = np.argsort(scores)[::-1]
    results: list[dict[str, Any]] = []
    for idx in ranked:
        score = float(scores[idx])
        if score < min_score:
            continue
        item = dict(chunks[idx])
        item["retrieval_score"] = round(score, 4)
        results.append(item)
        if len(results) >= top_k:
            break
    return results
