"""Canonical section registry — the single source of truth for *which*
sections an RFP can contain and how each one is produced.

Historically the section list lived in three disconnected places:

* ``Template.sections`` — display-only chips in the wizard (never drove
  generation, and used loose labels like ``"Eligibility"``);
* ``questionnaire.clause_plan`` — the hardcoded ``(clause_type, query)`` plan
  that actually drives generation (``"Eligibility Criteria"``);
* ``boilerplate.SECTION_KIND`` — fixed-vs-generated routing keyed on yet
  another set of labels.

The "custom sections" feature lets a user add or remove *any* section, so we
need one authoritative catalogue that every layer agrees on: canonical label,
retrieval query (for the RAG path), content kind, a UI group, and a fixed
document order. This module is that catalogue.
"""
from __future__ import annotations

from .boilerplate import kind_for

# UI groups (purely for how the picker is laid out).
GROUP_STANDARD = "Standard / legal"
GROUP_COMPUTED = "Computed"
GROUP_SPECIFIC = "Tender-specific"

# Canonical, ordered catalogue of every section the tool can produce.
# Order here == the order sections render in the final document. Each entry:
#   (label, retrieval_query, group)
# ``kind`` is derived from boilerplate.kind_for() so there is exactly one place
# that decides boilerplate vs parameterized vs generated.
_REGISTRY: list[tuple[str, str, str]] = [
    ("Disclaimer", "disclaimer", GROUP_STANDARD),
    ("Definitions", "definitions and abbreviations", GROUP_STANDARD),
    ("NIT", "advertised tender notice inviting publication threshold", GROUP_COMPUTED),
    ("ITB", "instructions to bidders mandatory sections", GROUP_STANDARD),
    ("BDS", "bidding data sheet bid data parameters", GROUP_SPECIFIC),
    ("Scope of Work", "scope of work technical specifications deliverables", GROUP_SPECIFIC),
    ("Terms of Reference", "terms of reference consulting objectives deliverables", GROUP_SPECIFIC),
    ("Eligibility Criteria", "eligibility qualification non-restrictive criteria", GROUP_SPECIFIC),
    ("Pre-Qualification", "pre-qualification criteria empanelment shortlisting", GROUP_SPECIFIC),
    ("Evaluation Criteria", "evaluation method QCBS L1 selection", GROUP_SPECIFIC),
    ("Bid Security (EMD)", "bid security earnest money deposit EMD goods", GROUP_COMPUTED),
    ("Performance Security", "performance security guarantee contract", GROUP_COMPUTED),
    ("Integrity Pact", "integrity pact high value transparency", GROUP_STANDARD),
    ("Make in India", "make in india local content preference PPP-MII", GROUP_STANDARD),
    ("MSE Preference", "MSE MSME purchase preference", GROUP_STANDARD),
    ("Confidentiality", "confidentiality non-disclosure", GROUP_STANDARD),
    ("GCC", "general conditions of contract", GROUP_STANDARD),
    ("SCC", "special conditions of contract", GROUP_SPECIFIC),
    ("Force Majeure", "force majeure", GROUP_STANDARD),
    ("Dispute Resolution", "dispute resolution arbitration", GROUP_STANDARD),
]

_QUERY = {label: query for label, query, _ in _REGISTRY}
_ORDER = {label: i for i, (label, _, _) in enumerate(_REGISTRY)}

# Loose / legacy labels (templates, older drafts) -> canonical label.
_ALIASES = {
    "Eligibility": "Eligibility Criteria",
    "Evaluation": "Evaluation Criteria",
    "Evaluation (QCBS)": "Evaluation Criteria",
    "Scope of Work / TOR": "Scope of Work",
    "TOR": "Terms of Reference",
    "EMD": "Bid Security (EMD)",
    "Bid Security": "Bid Security (EMD)",
}


def canonical(label: str) -> str | None:
    """Map any label (canonical, alias, or unknown) to its canonical form."""
    label = (label or "").strip()
    if label in _ORDER:
        return label
    return _ALIASES.get(label)


def is_valid(label: str) -> bool:
    return canonical(label) is not None


def query_for(label: str) -> str:
    """Retrieval query for a section (used only by the generated/RAG path)."""
    c = canonical(label) or label
    return _QUERY.get(c, c)


def normalize(labels) -> list[str]:
    """Canonicalize a list of labels: drop unknowns/blanks, dedupe (keep first
    occurrence), and sort into the fixed document order."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in labels or []:
        c = canonical(raw)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return sorted(out, key=lambda l: _ORDER[l])


def plan_for(labels) -> list[tuple[str, str]]:
    """Build a clause plan ``[(label, query), …]`` for a custom section set,
    in canonical document order."""
    return [(l, _QUERY[l]) for l in normalize(labels)]


def catalogue() -> list[dict]:
    """The full catalogue for the section picker (ordered)."""
    return [
        {"label": label, "query": query, "group": group, "kind": kind_for(label),
         "order": i}
        for i, (label, query, group) in enumerate(_REGISTRY)
    ]
