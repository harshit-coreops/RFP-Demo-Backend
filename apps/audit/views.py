from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.drafting.models import Draft

from .models import AuditRecord
from .services import verify_chain


@api_view(["GET"])
def draft_audit(request, draft_id):
    draft = Draft.objects.get(id=draft_id)
    records = AuditRecord.objects.filter(draft=draft).order_by("id")
    return Response(
        {
            "draft_id": draft_id,
            "chain": verify_chain(draft),
            "records": [
                {
                    "id": r.id,
                    "action": r.action,
                    "clause_ref": r.clause_ref,
                    "clause_text": r.clause_text,
                    "citation": r.citation,
                    "kb_version": r.kb_version,
                    "confidence": r.confidence,
                    "confidence_score": r.confidence_score,
                    "model": r.model,
                    "prompt_version": r.prompt_version,
                    "actor": r.actor,
                    "role": r.role,
                    "justification": r.justification,
                    "created_at": r.created_at,
                    "record_hash": r.record_hash[:12],
                    "prev_hash": r.prev_hash[:12],
                }
                for r in records
            ],
        }
    )
