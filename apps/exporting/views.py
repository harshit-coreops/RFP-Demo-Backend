from django.http import HttpResponse

from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.audit.services import record
from apps.drafting.models import Draft

from .builders import build_docx, build_pdf
from .preview import build_preview


@api_view(["GET"])
def preview(request, draft_id):
    """Read-only block preview of the composed document (editor canvas).

    Same source as the DOCX/PDF export (``compose_document``), so what the
    editor shows matches what is exported. No audit record — this is a read."""
    draft = Draft.objects.get(id=draft_id)
    return Response(build_preview(draft))


@api_view(["GET"])
def export_docx(request, draft_id):
    draft = Draft.objects.get(id=draft_id)
    data = build_docx(draft)
    record(draft, "export", justification="Exported DOCX with embedded citations.",
           metadata={"format": "docx"})
    resp = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    resp["Content-Disposition"] = f'attachment; filename="draft-{draft_id}.docx"'
    return resp


@api_view(["GET"])
def export_pdf(request, draft_id):
    draft = Draft.objects.get(id=draft_id)
    data = build_pdf(draft)
    record(draft, "export", justification="Exported PDF (archival).",
           metadata={"format": "pdf"})
    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="draft-{draft_id}.pdf"'
    return resp
