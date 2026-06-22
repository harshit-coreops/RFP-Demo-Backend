from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.audit.services import record
from apps.drafting.models import Clause, Draft

from .engine import find_similar, reuse_candidates
from .models import HistoricalClause, HistoricalDocument


def _query_for(data) -> str:
    if data.get("draft_id"):
        d = Draft.objects.get(id=data["draft_id"])
        return f"{d.instrument} {d.category} {d.title} {d.brief} " + " ".join(
            c.clause_type for c in d.clauses.all()
        )
    return data.get("text", "")


@api_view(["GET"])
def documents(request):
    docs = HistoricalDocument.objects.all()
    return Response([
        {"id": d.id, "title": d.title, "instrument": d.instrument, "category": d.category,
         "estimated_value_cr": d.estimated_value_cr, "year": d.year, "summary": d.summary,
         "tags": d.tags, "clause_count": d.clauses.count()}
        for d in docs
    ])


@api_view(["POST"])
def search(request):
    """FR-17/FR-35 — top-N similar documents + duplicate flag + reuse candidates."""
    query = _query_for(request.data)
    similar = find_similar(query, top_k=request.data.get("top_k", 5))
    similar["reuse_candidates"] = reuse_candidates(query, top_k=6)
    similar["query"] = query[:200]
    return Response(similar)


@api_view(["POST"])
def reuse(request):
    """Reuse a historical clause into a draft (creates a Clause + audit)."""
    draft = Draft.objects.get(id=request.data["draft_id"])
    hc = HistoricalClause.objects.get(id=request.data["clause_id"])
    order = draft.clauses.count()
    clause = Clause.objects.create(
        draft=draft, clause_type=hc.clause_type, text=hc.text,
        citations=[{"citation": hc.citation, "kb_version": "reuse", "score": 1.0}] if hc.citation else [],
        confidence="Medium", confidence_score=0.7, grounded=bool(hc.citation),
        rationale=f"Reused from historical document: {hc.document.title}",
        model="reuse", order=order,
    )
    record(
        draft, "edit", clause_ref=clause.clause_type, clause_text=clause.text,
        citation=hc.citation, justification=f"Clause reused from '{hc.document.title}' (FR-17).",
        metadata={"reuse_source_document_id": hc.document_id, "historical_clause_id": hc.id},
    )
    return Response({"reused_clause_id": clause.id, "clause_type": clause.clause_type})
