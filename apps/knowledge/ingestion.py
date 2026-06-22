"""Workflow 3 — Knowledge Base Update pipeline (§3.2.5, Workflow 3).

Ingest a new Office Memorandum / circular / guideline:
  classify → embed → duplicate-detect → conflict-flag → (HITL) approve → version.

Nothing enters the live KB without human approval. On approval the artefact is
written as a new Chunk in a freshly-versioned namespace so retrieval picks up
the update while prior drafts remain reproducible against their KB version.
"""
from __future__ import annotations

import json
import math
import re

from apps.llm.gateway import gateway

from .models import (Chunk, Document, IngestionJob, KnowledgeSource,
                     KnowledgeVersion)

DUPLICATE_THRESHOLD = 0.92
CONFLICT_THRESHOLD = 0.70

_CLASSIFY_SYSTEM = (
    "You classify Indian government procurement regulatory artefacts. Given the "
    "text, identify the governing framework (one of: GFR, DoE, GeM, PPP-MII, MSE, "
    "CVC, State, Other) and the artefact type (OM, circular, guideline, amendment). "
    'Respond ONLY as JSON: {"framework": str, "type": str, "tags": [str], "citation": str}'
)

_FRAMEWORK_HINTS = {
    "GFR": ["gfr", "general financial rule", "rule 1"],
    "GeM": ["gem", "government e-marketplace"],
    "PPP-MII": ["make in india", "local content", "ppp-mii", "dpiit"],
    "MSE": ["mse", "msme", "micro and small"],
    "CVC": ["integrity pact", "vigilance", "cvc"],
    "DoE": ["department of expenditure", "doe manual", "procurement manual"],
}


def _cosine(a, b):
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def _classify(text: str) -> dict:
    try:
        raw = gateway.complete_json(_CLASSIFY_SYSTEM, text[:4000])
        data = json.loads(raw) if raw.strip().startswith("{") else {}
        if data.get("framework"):
            return data
    except Exception:
        pass
    low = text.lower()
    fw = next((k for k, hints in _FRAMEWORK_HINTS.items() if any(h in low for h in hints)), "Other")
    dtype = "OM" if "office memorandum" in low or "o.m." in low else (
        "circular" if "circular" in low else "guideline")
    return {"framework": fw, "type": dtype, "tags": [], "citation": ""}


def analyse(source: KnowledgeSource, title: str, raw_text: str) -> IngestionJob:
    cls = _classify(raw_text)
    emb = gateway.embed([raw_text])[0]

    # Duplicate + conflict detection against existing chunks.
    dup, dup_score = None, 0.0
    conflict, conflict_score = None, 0.0
    fw = cls.get("framework", "")
    for ch in Chunk.objects.all():
        if not ch.embedding:
            continue
        score = _cosine(emb, ch.embedding)
        if score > dup_score:
            dup, dup_score = ch, score
        # Same framework, topically close but not identical => potential update/conflict.
        if fw and fw.lower() in (ch.citation.lower() + " " + " ".join(ch.tags).lower()):
            if CONFLICT_THRESHOLD <= score < DUPLICATE_THRESHOLD and score > conflict_score:
                conflict, conflict_score = ch, score

    job = IngestionJob.objects.create(
        source=source, title=title,
        citation=cls.get("citation") or f"{fw} — {title}"[:128],
        raw_text=raw_text, classified_framework=fw,
        classified_type=cls.get("type", "guideline"), tags=cls.get("tags", []),
        embedding=emb,
        duplicate_of=dup if dup_score >= DUPLICATE_THRESHOLD else None,
        duplicate_score=round(dup_score, 4),
        conflicts_with=conflict, conflict_score=round(conflict_score, 4),
    )
    if job.duplicate_of:
        job.note = f"Near-duplicate of existing chunk #{job.duplicate_of_id} ({job.duplicate_score})."
    elif job.conflicts_with:
        job.note = (f"May update/supersede existing chunk #{job.conflicts_with_id} "
                    f"({job.conflict_score}). Needs reviewer decision.")
    else:
        job.note = "No duplicate or conflict detected."
    job.save()
    return job


def _snippet(text: str, n: int = 220) -> str:
    text = " ".join((text or "").split())
    return text[:n] + ("…" if len(text) > n else "")


def compute_diffs(job: IngestionJob) -> list[dict]:
    """Structured before/after rule diffs for the KB admin review screen.

    Derives the change type from duplicate/conflict detection: a conflicting
    existing chunk → MODIFY/CONFLICT (before = its text, after = the artefact);
    otherwise ADD (a brand-new rule)."""
    fw = job.classified_framework or "—"
    conf = "High" if job.duplicate_score >= 0.6 or job.conflict_score >= 0.6 else "Medium"
    diffs: list[dict] = []
    if job.conflicts_with_id:
        ch = job.conflicts_with
        diffs.append({
            "type": "CONFLICT", "framework": fw,
            "rule": ch.citation, "confidence": conf,
            "before": _snippet(ch.text),
            "after": _snippet(job.raw_text),
        })
    elif job.duplicate_of_id:
        ch = job.duplicate_of
        diffs.append({
            "type": "MODIFY", "framework": fw,
            "rule": ch.citation, "confidence": conf,
            "before": _snippet(ch.text),
            "after": _snippet(job.raw_text),
        })
    diffs.append({
        "type": "ADD", "framework": fw,
        "rule": job.citation or f"{fw} — {job.title}", "confidence": conf,
        "before": None,
        "after": _snippet(job.raw_text),
    })
    return diffs


def approve(job: IngestionJob, bump_version: bool = True) -> Chunk:
    """HITL approval: write the artefact into a freshly-versioned namespace."""
    src = job.source
    if bump_version:
        # New immutable KB version so prior drafts stay reproducible.
        base = re.sub(r"_r\d+$", "", src.version)
        rev = 1
        m = re.search(r"_r(\d+)$", src.version)
        if m:
            rev = int(m.group(1)) + 1
        src.version = f"{base}_r{rev}"
        src.save()
    doc = Document.objects.create(source=src, title=job.title)
    chunk = Chunk.objects.create(
        document=doc, source=src, citation=job.citation,
        heading=job.title, text=job.raw_text, tags=job.tags, embedding=job.embedding,
    )
    if bump_version:
        KnowledgeVersion.objects.create(
            source=src, version=src.version, title=job.title,
            published_by="knowledge.admin")
    job.status = IngestionJob.ST_APPROVED
    job.created_chunk = chunk
    job.note += f" → Approved into {src.namespace} as chunk #{chunk.id}."
    job.save()
    return chunk
