"""Hybrid retrieval (dense + lexical) with a lightweight reranker.

Mirrors the A&M RAG design: "Retrieval is hybrid (dense + keyword), followed
by a reranker; context binds each candidate to its citation, and a 'no rule
found' guard blocks ungrounded clauses." For the SQLite dev path this scans
chunks in Python (corpus is small and curated); the pgvector path replaces
the dense step with an ANN query without changing the interface.
"""
from __future__ import annotations

import math
import re

from apps.llm.gateway import Source, gateway

from .models import Chunk

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def _lexical(query_tokens: set[str], chunk: Chunk) -> float:
    ct = _tokens(chunk.text + " " + chunk.heading + " " + " ".join(chunk.tags))
    if not ct:
        return 0.0
    overlap = sum(1 for t in ct if t in query_tokens)
    return overlap / math.sqrt(len(ct))


def retrieve(query: str, namespaces: list[str] | None = None, top_k: int = 4) -> list[Source]:
    """Return reranked, citation-bound sources for a query."""
    qs = Chunk.objects.select_related("source", "document").all()
    if namespaces:
        keys = {ns.split(".")[0] for ns in namespaces}
        qs = qs.filter(source__key__in=keys)
    chunks = list(qs)
    if not chunks:
        return []

    q_emb = gateway.embed([query])[0]
    q_tokens = set(_tokens(query))

    scored = []
    for c in chunks:
        dense = _cosine(q_emb, c.embedding) if c.embedding else 0.0
        lex = _lexical(q_tokens, c)
        # Hybrid score, then a rerank boost for tag/citation keyword hits.
        hybrid = 0.65 * dense + 0.35 * lex
        boost = 0.0
        for tag in c.tags:
            if tag.lower() in query.lower():
                boost += 0.08
        if any(tok in c.citation.lower() for tok in q_tokens):
            boost += 0.05
        scored.append((hybrid + boost, dense, lex, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Reranker cut: keep candidates with non-trivial relevance.
    results: list[Source] = []
    for combined, dense, lex, c in scored[: max(top_k, 1)]:
        if combined <= 0.02:
            continue
        results.append(
            Source(
                chunk_id=c.id,
                citation=c.citation,
                kb_version=c.kb_version,
                text=c.text,
                score=round(min(combined, 1.0), 4),
            )
        )
    return results
