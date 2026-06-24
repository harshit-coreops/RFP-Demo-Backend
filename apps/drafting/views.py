from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.accounts.identity import actor_role
from apps.audit.services import record
from apps.compliance.service import report_for

from .generation import generate_section
from .intake import classify_brief, extract_text
from .models import Clause, Draft, Template
from .questionnaire import clause_plan, next_questions
from .recommendation import recommend
from .sections import catalogue, is_valid, normalize
from .serializers import DraftListSerializer, DraftSerializer, TemplateSerializer


def _compliance_for(draft) -> dict:
    return report_for(draft)


@api_view(["GET", "POST"])
def drafts(request):
    if request.method == "POST":
        d = request.data
        draft = Draft.objects.create(
            title=d.get("title", "Untitled procurement"),
            instrument=d.get("instrument", "RFP"),
            category=d.get("category", "Goods"),
            estimated_value_cr=d.get("estimated_value_cr", 0) or 0,
            selection_method=d.get("selection_method", "QCBS"),
            brief=d.get("brief", ""),
            namespaces=d.get("namespaces", []),
            answers=d.get("answers", {}),
        )
        return Response(DraftSerializer(draft).data, status=status.HTTP_201_CREATED)
    return Response(DraftListSerializer(Draft.objects.order_by("-id"), many=True).data)


@api_view(["GET", "PATCH", "DELETE"])
def draft_detail(request, draft_id):
    draft = Draft.objects.get(id=draft_id)
    if request.method == "DELETE":
        draft.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.method == "PATCH":
        for f in ["title", "category", "estimated_value_cr", "selection_method",
                  "brief", "namespaces", "answers"]:
            if f in request.data:
                setattr(draft, f, request.data[f])
        # Custom section set (Wizard step 2): validate labels against the
        # registry, drop unknowns/dupes, and store in canonical document order.
        if "custom_sections" in request.data:
            raw = request.data["custom_sections"] or []
            if not isinstance(raw, list):
                return Response({"detail": "custom_sections must be a list."},
                                status=status.HTTP_400_BAD_REQUEST)
            unknown = [s for s in raw if not is_valid(s)]
            if unknown:
                return Response({"detail": f"Unknown section(s): {unknown}"},
                                status=status.HTTP_400_BAD_REQUEST)
            draft.custom_sections = normalize(raw)
        if "use_custom_sections" in request.data:
            draft.use_custom_sections = bool(request.data["use_custom_sections"])
        draft.save()
    data = DraftSerializer(draft).data
    data["compliance"] = _compliance_for(draft)
    data["questionnaire"] = next_questions(draft)
    return Response(data)


@api_view(["POST"])
def classify(request, draft_id=None):
    """Wizard step 0 — classify a brief and/or extract text from uploads.

    Accepts JSON {brief} or multipart with one or more files. Returns the
    classification + a per-file extraction note (OCR path is used for scans)."""
    brief = request.data.get("brief", "") or ""
    files_note = []
    for f in request.FILES.getlist("files") or request.FILES.values():
        text, note = extract_text(f.name, f.read())
        files_note.append({"name": f.name, "chars": len(text), "note": note,
                           "parsed": bool(text.strip())})
        brief = f"{brief}\n\n{text}".strip()
    result = classify_brief(brief)
    result["files"] = files_note
    result["brief"] = brief[:6000]
    return Response(result)


@api_view(["GET"])
def recommendation(request, draft_id):
    """Wizard step 1 — recommend instrument + method (rules + LLM fallback)."""
    draft = Draft.objects.get(id=draft_id)
    return Response(recommend(draft.spec, draft.brief))


@api_view(["GET"])
def templates(request):
    """Wizard step 2 — template catalogue, optionally filtered."""
    qs = Template.objects.all()
    instrument = request.query_params.get("instrument")
    category = request.query_params.get("category")
    if instrument:
        qs = qs.filter(instrument=instrument)
    if category:
        qs = qs.filter(category=category)
    return Response(TemplateSerializer(qs.order_by("-recommended", "name"), many=True).data)


@api_view(["GET"])
def sections(request):
    """Wizard step 2 (custom) — the full catalogue of pickable sections."""
    return Response({"sections": catalogue()})


@api_view(["POST"])
def apply_template(request, draft_id):
    """Wizard step 2 — apply a chosen template to the draft (recorded)."""
    draft = Draft.objects.get(id=draft_id)
    tpl = Template.objects.get(key=request.data.get("template_key"))
    draft.template_key = tpl.key
    draft.instrument = tpl.instrument
    draft.category = tpl.category
    if tpl.selection_method:
        draft.selection_method = tpl.selection_method
    draft.use_custom_sections = False  # a real template overrides any custom pick
    draft.save()
    actor, role = actor_role(request)
    record(draft, "generate", clause_ref="template", actor=actor, role=role,
           justification=f"Applied template '{tpl.name}' ({tpl.version}).",
           metadata={"template_key": tpl.key, "sections": tpl.sections})
    return Response(DraftSerializer(draft).data)


@api_view(["POST"])
def questionnaire(request, draft_id):
    """Submit answers; returns the next adaptive questions + clause plan."""
    draft = Draft.objects.get(id=draft_id)
    answers = request.data.get("answers", {})
    draft.answers = {**(draft.answers or {}), **answers}
    if "category" in answers:
        draft.category = answers["category"]
    if "estimated_value_cr" in answers:
        draft.estimated_value_cr = float(answers["estimated_value_cr"] or 0)
    if "selection_method" in answers:
        draft.selection_method = answers["selection_method"]
    draft.save()
    return Response({
        "questionnaire": next_questions(draft),
        "clause_plan": [{"clause_type": t, "query": q} for t, q in clause_plan(draft)],
    })


@api_view(["POST"])
def generate(request, draft_id):
    """Generate one clause (worked-example demo) or the whole plan."""
    draft = Draft.objects.get(id=draft_id)
    plan = dict((t, q) for t, q in clause_plan(draft))
    target = request.data.get("clause_type")

    if target:
        query = plan.get(target, request.data.get("query", target))
        order = len(plan) and list(plan).index(target) if target in plan else draft.clauses.count()
        clause = generate_section(draft, target, query, order=order)
        return Response(DraftSerializer(draft).data | {"generated": clause.id,
                                                       "compliance": _compliance_for(draft)})

    # generate_all
    draft.clauses.all().delete()
    for i, (ctype, query) in enumerate(clause_plan(draft)):
        generate_section(draft, ctype, query, order=i)
    data = DraftSerializer(draft).data
    data["compliance"] = _compliance_for(draft)
    return Response(data)


@api_view(["POST"])
def accept_clause(request, draft_id, clause_id):
    draft = Draft.objects.get(id=draft_id)
    clause = Clause.objects.get(id=clause_id, draft=draft)
    edited = request.data.get("text")
    action = "accept"
    if edited is not None and edited != clause.text:
        clause.text = edited
        action = "edit"
    clause.accepted = True
    clause.save()
    record(
        draft, action, clause_ref=clause.clause_type, clause_text=clause.text,
        citation="; ".join(c["citation"] for c in clause.citations),
        kb_version="; ".join(sorted({c["kb_version"] for c in clause.citations})),
        confidence=clause.confidence, confidence_score=clause.confidence_score,
        model=clause.model, prompt_version=clause.prompt_version,
        justification=request.data.get("justification", ""),
    )
    return Response(DraftSerializer(draft).data | {"compliance": _compliance_for(draft)})


@api_view(["GET"])
def draft_suggestions(request, draft_id):
    """In-editor AI suggestions for a draft (Editor right panel · FR-22).

    Reuses the Workflow-2 review engine bound to this draft so the editor and
    the standalone Review screen share one suggestion lifecycle. The returned
    review_id is used to accept/modify/reject via the existing /reviews/ act
    endpoint."""
    from apps.review.engine import run_review
    from apps.review.models import ReviewSession
    from apps.review.serializers import ReviewSessionSerializer

    draft = Draft.objects.get(id=draft_id)
    session = ReviewSession.objects.filter(draft=draft).order_by("-id").first()
    refresh = request.query_params.get("refresh") == "1"
    if session is None or refresh:
        if session is None:
            session = ReviewSession.objects.create(
                draft=draft, title=f"In-editor review of {draft}",
                instrument=draft.instrument)
        run_review(session)
    return Response(ReviewSessionSerializer(session).data)


@api_view(["POST"])
def finalise(request, draft_id):
    """Finalisation gate: blocked while critical/high compliance issues are open.

    Pass lock=true (from the Export modal) to lock the version as the official
    output and record it to the audit trail."""
    draft = Draft.objects.get(id=draft_id)
    report = _compliance_for(draft)
    if report["finalisation_blocked"]:
        return Response(
            {"finalised": False, "reason": "Compliance gate: unresolved critical/high issues.",
             "compliance": report},
            status=status.HTTP_409_CONFLICT,
        )
    low_conf = [c.clause_type for c in draft.clauses.filter(grounded=True)
                if c.confidence == "Low" and not c.accepted]
    if low_conf:
        return Response(
            {"finalised": False,
             "reason": f"Low-confidence clauses need explicit action (FR-47): {low_conf}",
             "compliance": report},
            status=status.HTTP_409_CONFLICT,
        )
    lock = bool(request.data.get("lock"))
    draft.status = "final"
    if lock:
        draft.locked = True
    draft.save()
    record(draft, "finalise",
           justification="All gates passed; marked Final Draft." +
                         (" Version locked as official output." if lock else ""),
           metadata={"verdict": report["verdict"], "locked": lock,
                     "version": f"v{draft.version}.0-final" if lock else f"v{draft.version}"})
    return Response({"finalised": True, "compliance": report,
                     "draft": DraftSerializer(draft).data})
