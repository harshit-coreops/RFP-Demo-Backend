"""Compliance & Validation Engine (A&M Section B / RFQ §3.2.3, FR-27).

A deterministic rule engine (thresholds, bid security, mandatory sections,
non-restrictive criteria) combined with per-guideline logical agents (GFR,
DoE, CVC, PPP-MII, MSE) — each tracing its findings to its governing
framework. A severity classifier grades findings; output is Pass / Warning /
Fail and a gate blocks finalisation until critical issues are resolved.
"""
from __future__ import annotations

import hashlib
import re

# Severity -> ordering
SEV_CRITICAL = "Critical"
SEV_HIGH = "High"
SEV_MEDIUM = "Medium"
SEV_LOW = "Low"
SEV_INFO = "Info"
_SEV_RANK = {SEV_CRITICAL: 4, SEV_HIGH: 3, SEV_MEDIUM: 2, SEV_LOW: 1, SEV_INFO: 0}

# Verdict per finding
FAIL, WARN, PASS = "Fail", "Warning", "Pass"

INTEGRITY_PACT_THRESHOLD_CR = 5.0
ADVERTISED_TENDER_THRESHOLD_CR = 0.25  # ₹25 lakh

MANDATORY_SECTIONS = ["NIT", "ITB", "Eligibility", "Evaluation", "GCC"]


def _has(clause_types: set[str], *needles: str) -> bool:
    joined = " ".join(clause_types).lower()
    return any(n.lower() in joined for n in needles)


def finding_key(framework: str, rule: str) -> str:
    """Stable identity for a finding so overrides bind across re-runs."""
    slug = re.sub(r"[^a-z0-9]+", "-", f"{framework} {rule}".lower()).strip("-")
    return slug or hashlib.sha1(f"{framework}{rule}".encode()).hexdigest()[:12]


def evaluate(spec: dict, clauses: list[dict], overrides=None) -> dict:
    """clauses: [{clause_type, text, ...}]. Returns a structured report.

    overrides: optional iterable of finding keys that a reviewer has overridden
    with a justification. Overridden findings stop blocking finalisation and are
    reported with overridden=True so the UI can show them as resolved."""
    overrides = set(overrides or [])
    value = float(spec.get("estimated_value_cr") or 0)
    category = (spec.get("category") or "Goods")
    types = {c.get("clause_type", "") for c in clauses}
    findings: list[dict] = []

    def add(framework, rule, severity, status, message):
        findings.append({
            "key": finding_key(framework, rule),
            "framework": framework, "rule": rule, "severity": severity,
            "status": status, "message": message,
        })

    # --- GFR agent ---
    if category.lower() == "goods":
        if _has(types, "Bid Security", "EMD", "Earnest Money"):
            add("GFR", "GFR 2017, Rule 170", SEV_INFO, PASS,
                "Bid Security clause present for a Goods procurement.")
        else:
            add("GFR", "GFR 2017, Rule 170", SEV_MEDIUM, WARN,
                "Bid Security (EMD) clause is recommended for Goods procurements "
                "(2%–5% of estimated value).")
        if not _has(types, "Performance Security", "Performance Guarantee"):
            add("GFR", "GFR 2017, Rule 171", SEV_LOW, WARN,
                "Performance Security clause (3%–10% of contract value) not detected.")

    # Tender method vs value band
    if value >= ADVERTISED_TENDER_THRESHOLD_CR:
        method = (spec.get("selection_method") or "").lower()
        if method in {"lte", "limited"}:
            add("GFR", "GFR 2017, Rule 161", SEV_HIGH, FAIL,
                f"Estimated value ₹{value} Cr (≥ ₹25 lakh) requires an Advertised "
                f"Tender Enquiry; Limited Tender is not permissible at this value.")
        else:
            add("GFR", "GFR 2017, Rule 161", SEV_INFO, PASS,
                "Advertised Tender Enquiry appropriate for the value band.")

    # --- CVC agent (Integrity Pact) ---
    if value >= INTEGRITY_PACT_THRESHOLD_CR:
        if _has(types, "Integrity Pact"):
            add("CVC", "CVC Integrity Pact Guidelines", SEV_INFO, PASS,
                f"Integrity Pact present (mandatory at ₹{value} Cr ≥ "
                f"₹{INTEGRITY_PACT_THRESHOLD_CR} Cr).")
        else:
            add("CVC", "CVC Integrity Pact Guidelines", SEV_CRITICAL, FAIL,
                f"Integrity Pact is mandatory for value ₹{value} Cr "
                f"(≥ ₹{INTEGRITY_PACT_THRESHOLD_CR} Cr) and is missing. "
                f"Finalisation is blocked until inserted.")

    # --- DoE agent (mandatory sections) ---
    missing = [s for s in MANDATORY_SECTIONS if not _has(types, s)]
    if missing:
        sev = SEV_HIGH if len(missing) >= 3 else SEV_MEDIUM
        add("DoE", "DoE Manual (Goods), Ch. 3", sev,
            FAIL if sev == SEV_HIGH else WARN,
            f"Mandatory section(s) not yet drafted: {', '.join(missing)}.")
    else:
        add("DoE", "DoE Manual (Goods), Ch. 3", SEV_INFO, PASS,
            "All checked mandatory sections are present.")

    # --- PPP-MII & MSE agents ---
    if category.lower() == "goods":
        if not _has(types, "Make in India", "Local Content", "PPP-MII"):
            add("PPP-MII", "PPP-MII Order 2017", SEV_MEDIUM, WARN,
                "Make-in-India local-content preference clause not detected.")
        if not _has(types, "MSE", "MSME"):
            add("MSE", "MSE Order 2012", SEV_LOW, WARN,
                "MSE purchase-preference clause not detected.")

    # Mark overridden findings (reviewer accepted the risk with justification).
    for f in findings:
        f["overridden"] = f["key"] in overrides and f["status"] != PASS

    # --- Aggregate verdict + gate (overridden findings no longer count) ---
    active = [f for f in findings if not f["overridden"]]
    worst = max((_SEV_RANK[f["severity"]] for f in active), default=0)
    has_fail = any(f["status"] == FAIL for f in active)
    blocking = [f for f in active if f["status"] == FAIL and
                f["severity"] in {SEV_CRITICAL, SEV_HIGH}]

    if has_fail:
        verdict = FAIL
    elif any(f["status"] == WARN for f in active):
        verdict = WARN
    else:
        verdict = PASS

    overridden_n = sum(1 for f in findings if f["overridden"])
    return {
        "verdict": verdict,
        "finalisation_blocked": bool(blocking),
        "blocking_count": len(blocking),
        "worst_severity": next((k for k, v in _SEV_RANK.items() if v == worst), SEV_INFO),
        "findings": findings,
        "summary": {
            "fail": sum(1 for f in active if f["status"] == FAIL),
            "warning": sum(1 for f in active if f["status"] == WARN),
            "pass": sum(1 for f in findings if f["status"] == PASS),
            "overridden": overridden_n,
            "total": len(findings),
        },
    }
