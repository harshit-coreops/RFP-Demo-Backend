"""Workflow 2 — AI-Based Review & Suggestion engine (RFQ §3.5.2).

Two layers, merged:
  1. Deterministic lint — ambiguity, restrictive-criteria and structure
     heuristics, plus the compliance engine's findings. Always runs (offline).
  2. LLM review — one grounded call that proposes clearer phrasing and flags
     issues the heuristics miss. Additive and best-effort.

Every suggestion is explainable (issue + rationale), traceable (target +
optional citation) and actionable (accept / modify / reject).
"""
from __future__ import annotations

import json
import re

from apps.compliance.engine import evaluate
from apps.llm.gateway import gateway

from .models import Suggestion

# Ambiguity / vagueness triggers.
_AMBIGUOUS = [
    "etc.", "as appropriate", "as required", "as applicable", "suitable",
    "reasonable", "and/or", "if needed", "to be decided", "tbd", "as deemed fit",
]
# Restrictive / non-competitive triggers (GFR Rule 173).
_RESTRICTIVE = [
    "only", "sole", "oem", "brand", "make of", "proprietary", "single source",
    "must be registered with", "preferred vendor",
]

_REVIEW_SYSTEM = (
    "You are a senior government procurement reviewer in India. Review the "
    "supplied procurement clauses for: ambiguity, restrictive/non-competitive "
    "criteria (GFR Rule 173), compliance risk, clarity and structure. For each "
    "issue propose improved phrasing aligned with standard drafting practice. "
    "Do NOT invent rules. For each issue, copy the exact problematic phrase "
    "from the clause verbatim into \"span\" (leave it \"\" only when the issue "
    "is that something is missing). Respond ONLY as JSON: "
    '{"suggestions": [{"target": str, "category": '
    '"Ambiguity|Restrictive|Compliance|Clarity|Structure|Missing", '
    '"severity": "Critical|High|Medium|Low|Info", "issue": str, '
    '"span": str, "suggested_text": str, "rationale": str}]}'
)


def _find_span(text: str, needle: str) -> str:
    """Return the matched substring with its original casing (empty if absent)."""
    i = text.lower().find(needle.lower())
    return text[i:i + len(needle)] if i >= 0 else needle


def _lint(target: str, text: str) -> list[dict]:
    out = []
    low = text.lower()
    for w in _AMBIGUOUS:
        if w in low:
            out.append({
                "target": target, "category": "Ambiguity", "severity": "Low",
                "issue": f"Vague wording '{w}' reduces enforceability.",
                "span": _find_span(text, w), "suggested_text": "", "origin": "lint",
                "rationale": "Replace open-ended phrasing with specific, measurable terms.",
            })
            break
    for w in _RESTRICTIVE:
        if re.search(rf"\b{re.escape(w)}\b", low):
            out.append({
                "target": target, "category": "Restrictive", "severity": "High",
                "issue": f"Potentially restrictive term '{w}' may limit competition.",
                "span": _find_span(text, w), "suggested_text": "", "origin": "lint",
                "citation": "GFR 2017, Rule 173",
                "rationale": "Eligibility/specs must be non-discriminatory (GFR Rule 173).",
            })
            break
    # Structure: overly long sentences hurt readability.
    for sentence in re.split(r"(?<=[.;])\s+", text):
        if len(sentence.split()) > 60:
            out.append({
                "target": target, "category": "Structure", "severity": "Low",
                "issue": "Sentence exceeds 60 words; split for clarity.",
                "span": sentence.strip(), "suggested_text": "", "origin": "lint",
                "rationale": "Shorter sentences improve readability and reduce ambiguity.",
            })
            break
    return out


def _compliance_suggestions(draft) -> list[dict]:
    clauses = [{"clause_type": c.clause_type, "text": c.text} for c in draft.clauses.all()]
    report = evaluate(draft.spec, clauses)
    out = []
    for f in report["findings"]:
        if f["status"] == "Pass":
            continue
        out.append({
            "target": f["framework"], "category":
            "Missing" if "not yet drafted" in f["message"] or "not detected" in f["message"] else "Compliance",
            "severity": f["severity"], "issue": f["message"],
            "citation": f["rule"], "suggested_text": "", "origin": "compliance",
            "rationale": f"Flagged by the {f['framework']} compliance agent.",
        })
    return out


def _llm_review(items: list[tuple[str, str]]) -> list[dict]:
    if not items:
        return []
    block = "\n\n".join(f"### {t}\n{txt}" for t, txt in items)
    prompt = f"Review these clauses and return JSON suggestions.\n\n{block}"
    try:
        raw = gateway.complete_json(_REVIEW_SYSTEM, prompt)
        data = json.loads(raw) if raw.strip().startswith("{") else {}
        sugg = data.get("suggestions", [])
    except Exception:
        return []
    out = []
    for s in sugg:
        if not isinstance(s, dict):
            continue
        out.append({
            "target": s.get("target", "Document"),
            "category": s.get("category", "Clarity"),
            "severity": s.get("severity", "Medium"),
            "issue": s.get("issue", ""),
            "span": s.get("span", ""),
            "suggested_text": s.get("suggested_text", ""),
            "rationale": s.get("rationale", ""),
            "origin": "llm",
        })
    return out


def _items_for(session) -> list[tuple[str, str]]:
    if session.draft:
        return [(c.clause_type, c.text) for c in session.draft.clauses.all()]
    # Split uploaded/pasted text into pseudo-sections on blank lines.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", session.source_text) if b.strip()]
    items = []
    for i, b in enumerate(blocks, 1):
        first = b.splitlines()[0][:60]
        items.append((first if len(first) > 8 else f"Section {i}", b))
    return items


def run_review(session) -> int:
    """Generate suggestions for a session. Returns count created."""
    session.suggestions.all().delete()
    items = _items_for(session)
    clause_index = {}
    if session.draft:
        clause_index = {c.clause_type: c.id for c in session.draft.clauses.all()}

    collected: list[dict] = []
    if session.draft:
        collected += _compliance_suggestions(session.draft)
    for target, text in items:
        collected += _lint(target, text)
    collected += _llm_review(items)

    created = 0
    for s in collected:
        Suggestion.objects.create(
            session=session,
            target=s.get("target", "Document"),
            category=s.get("category", "Clarity"),
            severity=s.get("severity", "Medium"),
            issue=s.get("issue", ""),
            original_text=dict(items).get(s.get("target", ""), ""),
            span=s.get("span", ""),
            suggested_text=s.get("suggested_text", ""),
            rationale=s.get("rationale", ""),
            citation=s.get("citation", ""),
            origin=s.get("origin", "llm"),
            clause_id=clause_index.get(s.get("target")),
        )
        created += 1
    return created
