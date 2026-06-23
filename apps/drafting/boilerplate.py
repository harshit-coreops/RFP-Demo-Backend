"""Fixed vs. variable section routing for the standard RFP *format*.

A government RFP is two kinds of content welded together:

* **boilerplate**  — standard legal/procedural text that is identical across
  tenders (disclaimer, ITB, GCC, Integrity Pact, force majeure, arbitration).
  These do NOT need retrieval or a faithfulness check; generating them via the
  LLM only wastes tokens and risks the FR-13 "no rule found" guard blocking
  text that is genuinely standard.
* **parameterized** — boilerplate prose with a handful of ``{{slot}}`` values
  computed deterministically from the Draft (EMD = 2% of value, PSG = 10%,
  bid-validity period, …). The clause text is fixed; only the numbers move.
* **generated** — everything genuinely tender-specific (scope of work, terms of
  reference, eligibility, evaluation). This is the only content that goes
  through the RAG + grounded-generation pipeline.

``kind_for()`` is the single dispatch point used by ``generation.py``.
"""
from __future__ import annotations

# clause_type -> kind. Anything not listed defaults to "generated".
SECTION_KIND = {
    # --- boilerplate (verbatim) ---
    "Disclaimer": "boilerplate",
    "Definitions": "boilerplate",
    "ITB": "boilerplate",
    "GCC": "boilerplate",
    "Integrity Pact": "boilerplate",
    "Make in India": "boilerplate",
    "MSE Preference": "boilerplate",
    "Force Majeure": "boilerplate",
    "Dispute Resolution": "boilerplate",
    "Confidentiality": "boilerplate",
    # --- parameterized (text fixed, numbers computed) ---
    "NIT": "parameterized",
    "Bid Security (EMD)": "parameterized",
    "Performance Security": "parameterized",
    # everything else (Scope of Work, Terms of Reference, Eligibility Criteria,
    # Evaluation Criteria, Pre-Qualification, BDS, SCC) -> "generated"
}


def kind_for(clause_type: str) -> str:
    return SECTION_KIND.get(clause_type, "generated")


def is_library(clause_type: str) -> bool:
    return kind_for(clause_type) in ("boilerplate", "parameterized")


# --- deterministic slot values (no LLM, no wall-clock dependence) ---------
EMD_PERCENT = 2.0            # GFR 2017 Rule 170: bid security 2–5% of value
PSG_PERCENT = 10.0           # GFR 2017 Rule 171: performance security 5–10%
BID_VALIDITY_DAYS = 180
INTEGRITY_PACT_THRESHOLD_CR = 5.0
_RUPEES_PER_CRORE = 1_00_00_000


def _group_inr(n: int) -> str:
    """Indian digit grouping: 12345678 -> 1,23,45,678."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    last3, rest = s[-3:], s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


def _inr_cr(cr: float) -> str:
    """Render a ₹-crore figure as ``₹1,00,00,000 (₹1 crore)``."""
    cr = cr or 0
    rupees = round(cr * _RUPEES_PER_CRORE)
    crore_txt = f"{cr:.2f}".rstrip("0").rstrip(".")
    return f"₹{_group_inr(rupees)} (₹{crore_txt} crore)"


def compute_slots(draft) -> dict:
    """Values injected into parameterized clause bodies."""
    val_cr = draft.estimated_value_cr or 0
    return {
        "estimated_value": _inr_cr(val_cr),
        "emd_percent": f"{EMD_PERCENT:g}%",
        "emd_amount": _inr_cr(val_cr * EMD_PERCENT / 100),
        "psg_percent": f"{PSG_PERCENT:g}%",
        "psg_amount": _inr_cr(val_cr * PSG_PERCENT / 100),
        "bid_validity_days": str(BID_VALIDITY_DAYS),
        "integrity_pact_threshold": f"₹{INTEGRITY_PACT_THRESHOLD_CR:g} crore",
        "instrument": draft.instrument,
        "category": draft.category,
        "selection_method": draft.selection_method or "as specified in the bid documents",
        "title": draft.title or "the captioned procurement",
    }


def fill(body: str, slots: dict) -> str:
    out = body
    for key, value in slots.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out
