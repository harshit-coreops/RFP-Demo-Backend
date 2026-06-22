"""Similarity & reuse engine (FR-17 top-N similar; FR-35 duplicate detection).

Semantic search over the historical-document corpus using the same embedding
provider as RAG. Near-duplicates are flagged above a cosine threshold.
"""
from __future__ import annotations

import math

from apps.llm.gateway import gateway

from .models import HistoricalClause, HistoricalDocument

DUPLICATE_THRESHOLD = 0.86
SIMILAR_THRESHOLD = 0.50
REUSE_THRESHOLD = 0.28   # clause-level reuse suggestions use a lower floor


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def find_similar(query_text: str, top_k: int = 5) -> dict:
    q = gateway.embed([query_text])[0]
    scored = []
    for doc in HistoricalDocument.objects.all():
        if not doc.embedding:
            continue
        score = _cosine(q, doc.embedding)
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:top_k]:
        if score < SIMILAR_THRESHOLD:
            continue
        results.append({
            "id": doc.id, "title": doc.title, "instrument": doc.instrument,
            "category": doc.category, "estimated_value_cr": doc.estimated_value_cr,
            "year": doc.year, "summary": doc.summary, "tags": doc.tags,
            "score": round(score, 4),
            "duplicate": score >= DUPLICATE_THRESHOLD,
        })
    return {
        "results": results,
        "duplicate_found": any(r["duplicate"] for r in results),
    }


def reuse_candidates(query_text: str, top_k: int = 6) -> list[dict]:
    q = gateway.embed([query_text])[0]
    scored = []
    for cl in HistoricalClause.objects.select_related("document").all():
        if not cl.embedding:
            continue
        scored.append((_cosine(q, cl.embedding), cl))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, cl in scored[:top_k]:
        if score < REUSE_THRESHOLD:
            continue
        out.append({
            "id": cl.id, "clause_type": cl.clause_type, "text": cl.text,
            "citation": cl.citation, "source_document": cl.document.title,
            "score": round(score, 4),
        })
    return out
