from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.audit.services import record
from apps.drafting.models import Clause, Draft

from .engine import run_review
from .models import ReviewSession, Suggestion
from .serializers import ReviewSessionSerializer


@api_view(["GET", "POST"])
def reviews(request):
    if request.method == "POST":
        d = request.data
        draft = None
        if d.get("draft_id"):
            draft = Draft.objects.get(id=d["draft_id"])
        session = ReviewSession.objects.create(
            draft=draft,
            title=d.get("title") or (f"Review of {draft}" if draft else "Uploaded draft review"),
            instrument=d.get("instrument", draft.instrument if draft else ""),
            source_text=d.get("text", ""),
        )
        run_review(session)
        return Response(ReviewSessionSerializer(session).data, status=status.HTTP_201_CREATED)
    return Response(ReviewSessionSerializer(ReviewSession.objects.order_by("-id"), many=True).data)


@api_view(["GET", "POST"])
def review_detail(request, review_id):
    session = ReviewSession.objects.get(id=review_id)
    if request.method == "POST":  # re-run
        run_review(session)
    return Response(ReviewSessionSerializer(session).data)


@api_view(["POST"])
def act(request, review_id, suggestion_id):
    """Accept / modify / reject a suggestion (HITL)."""
    s = Suggestion.objects.get(id=suggestion_id, session_id=review_id)
    action = request.data.get("action")  # accept | modify | reject
    if action == "reject":
        s.status = "rejected"
    elif action in ("accept", "modify"):
        s.status = "modified" if action == "modify" else "accepted"
        s.final_text = request.data.get("text", s.suggested_text)
    s.save()
    return Response(ReviewSessionSerializer(s.session).data)


@api_view(["POST"])
def apply_to_draft(request, review_id):
    """Apply accepted/modified suggestions that target a clause back into the
    draft, recording each change in the immutable audit trail."""
    session = ReviewSession.objects.get(id=review_id)
    if not session.draft:
        return Response({"applied": 0, "reason": "No linked draft (uploaded-text review)."})
    applied = 0
    for s in session.suggestions.filter(status__in=["accepted", "modified"]):
        if not s.clause_id or not s.final_text:
            continue
        try:
            clause = Clause.objects.get(id=s.clause_id, draft=session.draft)
        except Clause.DoesNotExist:
            continue
        clause.text = s.final_text
        clause.accepted = True
        clause.save()
        record(
            session.draft, "edit", clause_ref=clause.clause_type,
            clause_text=clause.text, confidence=clause.confidence,
            confidence_score=clause.confidence_score, model=clause.model,
            justification=f"Workflow-2 review applied ({s.category}): {s.issue[:120]}",
            metadata={"review_id": session.id, "suggestion_id": s.id},
        )
        applied += 1
    return Response({"applied": applied, "review": ReviewSessionSerializer(session).data})
