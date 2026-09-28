from __future__ import annotations

import uuid
from collections import defaultdict, deque
from typing import Any

from ..storage import get_store
from .seed import CONCEPTS, RELATIONSHIPS


def ensure_seeded() -> None:
    store = get_store()
    existing = {c["name"]: c for c in store.list_kg_concepts()}
    if len(existing) >= len(CONCEPTS):
        return
    for _key, name, domain, description, difficulty in CONCEPTS:
        existing_row = existing.get(name)
        cid = existing_row["id"] if existing_row else str(uuid.uuid4())
        store.upsert_kg_concept(
            {
                "id": cid,
                "name": name,
                "domain": domain,
                "description": description,
                "difficulty": difficulty,
            }
        )
    by_name = {c["name"]: c["id"] for c in store.list_kg_concepts()}
    name_for_key = {key: name for key, name, *_ in CONCEPTS}
    for src, dst, rel in RELATIONSHIPS:
        source_id = by_name.get(name_for_key[src])
        target_id = by_name.get(name_for_key[dst])
        if not source_id or not target_id:
            continue
        store.upsert_kg_relationship(
            {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "target_id": target_id,
                "relation": rel,
                "weight": 1.0,
            }
        )


def graph_payload() -> dict[str, Any]:
    ensure_seeded()
    store = get_store()
    return {"concepts": store.list_kg_concepts(), "relationships": store.list_kg_relationships()}


def _indexes() -> tuple[dict[str, dict], dict[str, str], list[dict]]:
    ensure_seeded()
    store = get_store()
    concepts = store.list_kg_concepts()
    rels = store.list_kg_relationships()
    by_id = {c["id"]: c for c in concepts}
    by_name = {c["name"].lower(): c["id"] for c in concepts}
    return by_id, by_name, rels


def find_concept_id(name: str) -> str | None:
    _, by_name, _ = _indexes()
    key = (name or "").strip().lower()
    if key in by_name:
        return by_name[key]
    for cand, cid in by_name.items():
        if key in cand or cand in key:
            return cid
    return None


def prerequisites_for(concept_name: str, depth: int = 3) -> list[dict[str, Any]]:
    by_id, _, rels = _indexes()
    cid = find_concept_id(concept_name)
    if not cid:
        return []
    incoming = defaultdict(list)
    for rel in rels:
        if rel["relation"] in {"prerequisite", "includes"}:
            incoming[rel["target_id"]].append(rel["source_id"])
    found: list[dict[str, Any]] = []
    seen = {cid}
    queue = deque([(cid, 0)])
    while queue:
        node, d = queue.popleft()
        if d >= depth:
            continue
        for src in incoming.get(node, []):
            if src in seen:
                continue
            seen.add(src)
            concept = by_id.get(src)
            if concept:
                found.append({**concept, "distance": d + 1})
            queue.append((src, d + 1))
    return found


def recommended_next_concepts(weak_names: list[str]) -> list[dict[str, Any]]:
    ranked: dict[str, dict[str, Any]] = {}
    for name in weak_names:
        for prereq in prerequisites_for(name):
            current = ranked.get(prereq["id"])
            if not current or prereq["distance"] < current["distance"]:
                ranked[prereq["id"]] = {**prereq, "needed_for": name}
    return sorted(ranked.values(), key=lambda x: (x["distance"], x.get("difficulty", 1)))
