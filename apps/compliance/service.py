"""Shared compliance computation: always evaluates a draft with its persisted
per-finding overrides applied, so the finalisation gate is consistent across
the drafting, compliance and exporting apps."""
from __future__ import annotations

from .engine import evaluate
from .models import ComplianceOverride


def override_keys(draft) -> set[str]:
    return set(
        ComplianceOverride.objects.filter(draft=draft).values_list("finding_key", flat=True)
    )


def report_for(draft) -> dict:
    clauses = [{"clause_type": c.clause_type, "text": c.text} for c in draft.clauses.all()]
    return evaluate(draft.spec, clauses, overrides=override_keys(draft))
