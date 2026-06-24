"""Adaptive questionnaire (FR-14/FR-16, Workflow 1 Step 9-10).

Rule-based adaptive logic: questions and the resulting clause plan branch on
instrument, category and value band. (In production the conversational layer
is LLM-driven via the gateway; the branching contract is the same.)
"""
from __future__ import annotations

# Clause plan templates -> (clause_type, retrieval query)
_BASE_GOODS = [
    ("NIT", "advertised tender notice inviting publication threshold"),
    ("ITB", "instructions to bidders mandatory sections"),
    ("Eligibility Criteria", "eligibility qualification non-restrictive criteria"),
    ("Evaluation Criteria", "evaluation method QCBS L1 selection"),
    ("Bid Security (EMD)", "bid security earnest money deposit EMD goods"),
    ("Performance Security", "performance security guarantee contract"),
    ("Make in India", "make in india local content preference PPP-MII"),
    ("MSE Preference", "MSE MSME purchase preference"),
    ("GCC", "general conditions of contract"),
]

# Fixed-format wrapper sections (standard clause library; not RAG-generated).
_FIXED_FRONT = [
    ("Disclaimer", "disclaimer"),
    ("Definitions", "definitions and abbreviations"),
]
_FIXED_BACK = [
    ("Force Majeure", "force majeure"),
    ("Dispute Resolution", "dispute resolution arbitration"),
]


def next_questions(draft) -> list[dict]:
    """Return the adaptive question set given current answers."""
    a = draft.answers or {}
    qs = [
        {"id": "category", "label": "Procurement category",
         "type": "choice", "options": ["Goods", "Consulting", "Non-Consulting"],
         "value": draft.category},
        {"id": "estimated_value_cr", "label": "Estimated value (₹ crore)",
         "type": "number", "value": draft.estimated_value_cr},
    ]
    # Branch: value band drives method + high-value clauses.
    if (draft.estimated_value_cr or 0) >= 0.25:
        qs.append({"id": "selection_method", "label": "Selection method",
                   "type": "choice", "options": ["QCBS", "L1", "LTE"],
                   "value": draft.selection_method,
                   "hint": "≥ ₹25 lakh ⇒ Advertised Tender (GFR Rule 161)."})
    if (draft.estimated_value_cr or 0) >= 5:
        qs.append({"id": "integrity_pact_ack", "label":
                   "Integrity Pact is mandatory at ≥ ₹5 Cr — include it?",
                   "type": "choice", "options": ["Yes", "No"],
                   "value": a.get("integrity_pact_ack", "Yes"),
                   "hint": "CVC guidelines."})
    if draft.category == "Goods":
        qs.append({"id": "make_in_india", "label":
                   "Apply Make-in-India local-content preference?",
                   "type": "choice", "options": ["Yes", "No"],
                   "value": a.get("make_in_india", "Yes")})
    return qs


def clause_plan(draft) -> list[tuple[str, str]]:
    """Adaptive clause plan: which clauses to draft, given the answers.

    If the user hand-picked a section set in Wizard step 2 (custom mode), that
    explicit choice wins — generation honours exactly those sections, in the
    canonical document order. We fall back to the adaptive logic when custom
    mode is off or the picked set is (defensively) empty."""
    from .sections import plan_for

    if getattr(draft, "use_custom_sections", False):
        plan = plan_for(draft.custom_sections)
        if plan:
            return plan

    a = draft.answers or {}
    plan = list(_BASE_GOODS) if draft.category == "Goods" else [
        ("NIT", "advertised tender notice inviting publication"),
        ("ITB", "instructions to bidders mandatory sections"),
        ("Eligibility Criteria", "eligibility qualification non-restrictive criteria"),
        ("Evaluation Criteria", "evaluation method QCBS selection"),
        ("GCC", "general conditions of contract"),
    ]
    # High-value: insert Integrity Pact (mandatory).
    if (draft.estimated_value_cr or 0) >= 5 and a.get("integrity_pact_ack", "Yes") == "Yes":
        plan.insert(5, ("Integrity Pact", "integrity pact high value transparency"))
    if draft.category == "Goods" and a.get("make_in_india", "Yes") != "Yes":
        plan = [p for p in plan if p[0] != "Make in India"]
    # Wrap the variable core in the fixed-format boilerplate sections.
    return _FIXED_FRONT + plan + _FIXED_BACK
