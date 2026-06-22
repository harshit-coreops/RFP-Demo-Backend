"""Grounded generation + validation (A&M Section B — Intelligent Drafting).

For each clause: retrieve citation-bound sources from the selected namespaces,
generate strictly from them via the gateway, run a lightweight validation
model (faithfulness/structure) that can downgrade confidence, persist the
clause, and append an immutable audit record.
"""
from __future__ import annotations

import re

from apps.audit.services import record
from apps.knowledge.retrieval import retrieve

from apps.llm.gateway import gateway

from .models import Clause

_FAITHFULNESS_MIN = 0.40  # min share of content terms supported by the sources


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def _validate(draft_text: str, sources) -> tuple[bool, str]:
    """Faithfulness check (a lightweight stand-in for the validation model).

    A clause is faithful when a sufficient share of its content terms are
    supported by the retrieved source text — works for clean LLM output where
    the citation lives in metadata, not inline. Returns (ok, note)."""
    if not sources:
        return False, "No sources — ungrounded."
    content = _terms(draft_text)
    if not content:
        return False, "Empty draft."
    supported = set()
    for s in sources:
        supported |= _terms(s.text)
    ratio = sum(1 for w in content if w in supported) / len(content)
    if ratio >= _FAITHFULNESS_MIN:
        return True, f"Faithfulness check passed (source support {ratio:.0%})."
    return False, f"Low source support ({ratio:.0%}) — possible unsupported content."


def generate_clause(draft, clause_type: str, query: str, order: int = 0) -> Clause:
    sources = retrieve(query, namespaces=draft.namespaces or None, top_k=4)
    spec = dict(draft.spec)
    spec["clause_type"] = clause_type
    result = gateway.generate_clause(spec, sources)

    ok, note = _validate(result.text, sources)
    confidence = result.confidence
    cscore = result.confidence_score
    grounded = result.grounded and ok
    text = result.text
    if result.grounded and not ok:
        # Validator overrides an over-confident draft.
        confidence, cscore = "Low", min(cscore, 0.3)
    if not grounded and len(text.strip()) < 20:
        # Ensure the "no rule found" guard always shows a clear notice (FR-13).
        text = (
            f"[No rule found] The model could not faithfully ground a "
            f"'{clause_type}' clause in the selected knowledge sources. Per FR-13, "
            f"no clause is generated without verifiable support. Broaden the sources "
            f"or refer this clause for manual drafting."
        )
        confidence, cscore = "Low", 0.0

    clause = Clause.objects.create(
        draft=draft,
        clause_type=clause_type,
        text=text,
        citations=result.citations,
        confidence=confidence,
        confidence_score=cscore,
        grounded=grounded,
        rationale=f"{result.rationale} | Validator: {note}",
        model=result.model or gateway.active_provider,
        prompt_version=result.prompt_version,
        order=order,
    )
    record(
        draft, "generate",
        clause_ref=clause_type,
        clause_text=clause.text,
        citation="; ".join(c["citation"] for c in result.citations),
        kb_version="; ".join(sorted({c["kb_version"] for c in result.citations})),
        confidence=confidence,
        confidence_score=cscore,
        model=clause.model,
        prompt_version=clause.prompt_version,
        metadata={"grounded": clause.grounded, "validator": note,
                  "retrieval_scores": [c.get("score") for c in result.citations]},
    )
    return clause
