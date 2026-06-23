"""Instrument + procurement-method recommendation (Wizard step 1).

Rules-first: deterministic logic over value band / category / brief keywords
decides the common cases with citations. When the rules are not confident
(ambiguous brief, unusual signals) it falls back to the LLM gateway, grounded
in the same thresholds. Every recommendation is overridable and the override
is recorded to the audit trail by the caller."""
from __future__ import annotations

import json

from apps.llm.gateway import gateway

# GFR / DoE thresholds (₹ crore)
ADVERTISED_TENDER_CR = 0.25   # ≥ ₹25 lakh ⇒ advertised (open) tender
LIMITED_TENDER_CEIL_CR = 0.25
INTEGRITY_PACT_CR = 5.0

_SERVICE_HINTS = ("consult", "advisory", "system integrator", "implementation",
                  "manpower", "services", "design", "audit")
_EMPANEL_HINTS = ("empanel", "panel", "rate contract", "framework agreement")
_EOI_HINTS = ("expression of interest", "eoi", "market sounding", "pre-qualification")


def _rule_based(spec: dict, brief: str) -> dict | None:
    """Return a recommendation dict or None if the rules are not confident."""
    value = float(spec.get("estimated_value_cr") or 0)
    category = (spec.get("category") or "Goods").lower()
    low = (brief or "").lower()

    citations = []
    # Instrument
    if any(h in low for h in _EOI_HINTS):
        instrument, conf = "EOI", "High"
        citations.append({"framework": "GFR 2017", "ref": "Rule 164", "note": "Two-stage / EOI for pre-qualification."})
    elif any(h in low for h in _EMPANEL_HINTS):
        instrument, conf = "RFE", "Medium"
        citations.append({"framework": "GFR 2017", "ref": "Rule 162", "note": "Empanelment / rate-contract route."})
    elif category == "goods":
        # Preference is RFP for Goods (technical + commercial split). Only a small,
        # simple supply — below the ₹25 lakh advertised-tender ceiling AND with no
        # installation / support / warranty scope — falls back to RFQ.
        simple_supply = value < ADVERTISED_TENDER_CR and not any(
            h in low for h in ("install", "support", "warranty", "commission",
                               "integrat", "amc", "o&m", "maintenance"))
        if simple_supply:
            instrument, conf = "RFQ", "Medium"
            citations.append({"framework": "DoE Manual", "ref": "Goods §3", "note": "Low-value simple supply ⇒ RFQ."})
        else:
            instrument, conf = "RFP", "High"
            citations.append({"framework": "DoE Manual", "ref": "Goods §4", "note": "Goods procurement (installation / support scope) ⇒ RFP with technical + commercial split."})
    elif category in ("consulting", "non-consulting"):
        instrument, conf = "RFP", "High"
        citations.append({"framework": "DoE Manual", "ref": "Consultancy", "note": "Selection of consultants ⇒ RFP."})
    else:
        return None  # not confident → LLM fallback

    # Method
    if value >= ADVERTISED_TENDER_CR:
        if category == "consulting":
            method, method_conf = "QCBS", "High"
            citations.append({"framework": "GFR 2017", "ref": "Rule 192", "note": "Quality-and-cost-based selection for consultancy."})
        else:
            method, method_conf = "Open Tender", "Review"
            citations.append({"framework": "GFR 2017", "ref": "Rule 161", "note": "Value above limited-tender ceiling ⇒ advertised (open) tender."})
    else:
        method, method_conf = "Limited Tender", "Medium"
        citations.append({"framework": "GFR 2017", "ref": "Rule 155", "note": "Below ₹25 lakh ⇒ limited tender enquiry permissible."})

    flags = []
    if value >= INTEGRITY_PACT_CR:
        flags.append("Integrity Pact mandatory (value ≥ ₹5 Cr, CVC).")

    return {
        "instrument": instrument, "instrument_confidence": conf,
        "method": method, "method_confidence": method_conf,
        "citations": citations, "flags": flags, "source": "rules",
        "rationale": "Derived from GFR/DoE thresholds for the stated value band and category.",
    }


_LLM_SYSTEM = (
    "You are an Indian government procurement advisor. Given a procurement brief "
    "and parameters, recommend the document instrument (RFP, RFQ, RFE or EOI) and "
    "the procurement method (Open Tender, Limited Tender, QCBS). Ground your answer "
    "in GFR 2017 and DoE manuals; do not invent rules. Respond ONLY as JSON: "
    '{"instrument": str, "instrument_confidence": "High|Medium|Low", '
    '"method": str, "method_confidence": "High|Medium|Review|Low", '
    '"citations": [{"framework": str, "ref": str, "note": str}], '
    '"flags": [str], "rationale": str}'
)


def _llm_based(spec: dict, brief: str) -> dict:
    prompt = (f"Brief: {brief}\n\nParameters: category={spec.get('category')}, "
              f"estimated_value_cr={spec.get('estimated_value_cr')}, "
              f"selection_method={spec.get('selection_method')}.")
    try:
        raw = gateway.complete_json(_LLM_SYSTEM, prompt)
        data = json.loads(raw) if raw.strip().startswith("{") else {}
        if data.get("instrument"):
            data.setdefault("citations", [])
            data.setdefault("flags", [])
            data["source"] = "llm"
            return data
    except Exception:
        pass
    # Conservative default if the model is offline.
    return {
        "instrument": spec.get("instrument", "RFP"), "instrument_confidence": "Low",
        "method": "Open Tender", "method_confidence": "Review",
        "citations": [{"framework": "GFR 2017", "ref": "Rule 161",
                       "note": "Default advertised tender pending manual confirmation."}],
        "flags": ["Low confidence — manual confirmation recommended."],
        "rationale": "Rules inconclusive and model offline; conservative default applied.",
        "source": "fallback",
    }


def _delegation_flag(value: float) -> str | None:
    """Annotate the approving authority from the Delegation of Financial Powers
    table (System Console · Config). Editing a ceiling changes this output."""
    try:
        from apps.accounts.models import DelegationCeiling
        ceilings = list(DelegationCeiling.objects.all())
    except Exception:
        return None
    if not ceilings:
        return None
    eligible = sorted((d for d in ceilings if d.ceiling_cr >= value), key=lambda d: d.ceiling_cr)
    if eligible:
        d = eligible[0]
        return f"Approving authority: {d.authority} ({d.unit}, ceiling ₹{d.ceiling_cr} Cr)."
    top = max(ceilings, key=lambda d: d.ceiling_cr)
    return (f"Value ₹{value} Cr exceeds all delegated ceilings (max ₹{top.ceiling_cr} Cr) — "
            f"requires higher approval / escalation.")


def recommend(spec: dict, brief: str = "") -> dict:
    rec = _rule_based(spec, brief)
    if rec is None:
        rec = _llm_based(spec, brief)
    flag = _delegation_flag(float(spec.get("estimated_value_cr") or 0))
    if flag:
        rec.setdefault("flags", []).append(flag)
    return rec
