from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.accounts.identity import actor_role
from apps.audit.services import record
from apps.drafting.models import Draft

from .models import ComplianceOverride
from .service import report_for


@api_view(["POST"])
def validate(request, draft_id):
    """Run the compliance engine on a draft (POST /compliance/validate)."""
    draft = Draft.objects.get(id=draft_id)
    report = report_for(draft)
    record(
        draft, "compliance",
        justification=f"Compliance run: {report['verdict']} "
                      f"({report['summary']['fail']} fail / "
                      f"{report['summary']['warning']} warning).",
        metadata={"verdict": report["verdict"],
                  "blocked": report["finalisation_blocked"]},
    )
    return Response(report)


@api_view(["POST", "DELETE"])
def override_finding(request, draft_id, finding_key):
    """Override (or clear) a single compliance finding with a justification (FR-30).

    POST body: {justification, framework?, rule?}. The override is persisted and
    written to the immutable audit trail; the gate recomputes without it."""
    draft = Draft.objects.get(id=draft_id)
    actor, role = actor_role(request)

    if request.method == "DELETE":
        ComplianceOverride.objects.filter(draft=draft, finding_key=finding_key).delete()
        record(draft, "compliance", clause_ref=finding_key, actor=actor, role=role,
               justification="Compliance override cleared.")
        return Response(report_for(draft))

    justification = (request.data.get("justification") or "").strip()
    if not justification:
        return Response({"error": "A justification is required to override a finding."},
                        status=status.HTTP_400_BAD_REQUEST)
    ov, _ = ComplianceOverride.objects.update_or_create(
        draft=draft, finding_key=finding_key,
        defaults={
            "framework": request.data.get("framework", ""),
            "rule": request.data.get("rule", ""),
            "justification": justification, "actor": actor, "role": role,
        },
    )
    record(
        draft, "override", clause_ref=finding_key, actor=actor, role=role,
        justification=justification,
        metadata={"framework": ov.framework, "rule": ov.rule, "finding_key": finding_key},
    )
    return Response(report_for(draft))
