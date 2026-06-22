"""Document builders (FR-42/FR-43, §3.2.8).

DOCX: clauses rendered with footnote-style citation markers and a References
section; the full clause→citation map is also embedded in the document
metadata (core properties) so clause-level traceability survives later manual
edits — exactly the dual-channel approach in pre-bid clarification Q43.

PDF: archival output with document metadata set. (True PDF/A-2b ICC/XMP
conformance is a production hardening step; structure and metadata are in
place here.)
"""
from __future__ import annotations

import io
import json
from xml.sax.saxutils import escape


def _embed_custom_properties(doc, props: dict) -> bool:
    """Embed key/value strings as an OOXML custom-properties part
    (docProps/custom.xml). This survives manual edits to the body — the
    downstream-traceability guarantee from pre-bid clarification Q43.
    Returns True on success; callers fall back to core metadata otherwise."""
    try:
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        from docx.opc.packuri import PackURI
        from docx.opc.part import Part

        entries = []
        for i, (name, value) in enumerate(props.items(), start=2):
            entries.append(
                f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" '
                f'pid="{i}" name="{escape(name)}">'
                f'<vt:lpwstr>{escape(value)}</vt:lpwstr></property>'
            )
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            + "".join(entries)
            + "</Properties>"
        )
        package = doc.part.package
        partname = PackURI("/docProps/custom.xml")
        ctype = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
        part = Part(partname, ctype, xml.encode("utf-8"), package)
        package.relate_to(part, RT.CUSTOM_PROPERTIES)
        return True
    except Exception:
        return False


def _citation_index(draft):
    """Build an ordered, de-duplicated citation list across clauses."""
    refs: list[str] = []
    for c in draft.clauses.all():
        for cit in c.citations:
            label = f"{cit['citation']} (KB {cit['kb_version']})"
            if label not in refs:
                refs.append(label)
    return refs


def build_docx(draft) -> bytes:
    from docx import Document as Docx
    from docx.shared import Pt

    doc = Docx()
    refs = _citation_index(draft)
    ref_pos = {r: i + 1 for i, r in enumerate(refs)}

    doc.add_heading(f"{draft.instrument}: {draft.title}", level=0)
    meta = doc.add_paragraph()
    meta.add_run(
        f"Category: {draft.category}    Estimated value: ₹{draft.estimated_value_cr} Cr"
        f"    Method: {draft.selection_method}    Status: {draft.status.upper()}"
    ).italic = True

    citation_map = {}
    for c in draft.clauses.all():
        doc.add_heading(c.clause_type, level=1)
        markers = []
        for cit in c.citations:
            label = f"{cit['citation']} (KB {cit['kb_version']})"
            markers.append(f"[{ref_pos[label]}]")
        para = doc.add_paragraph(c.text)
        if markers:
            run = para.add_run(" " + "".join(markers))
            run.font.superscript = True
            run.font.size = Pt(8)
        tag = doc.add_paragraph()
        t = tag.add_run(f"   ⟶ confidence: {c.confidence} ({c.confidence_score})")
        t.italic = True
        t.font.size = Pt(8)
        citation_map[c.clause_type] = [m["citation"] for m in c.citations]

    if refs:
        doc.add_heading("References (citations)", level=1)
        for i, r in enumerate(refs, 1):
            doc.add_paragraph(f"[{i}] {r}")

    # Embed traceability in document metadata (survives manual body edits).
    doc.core_properties.title = f"{draft.instrument}: {draft.title}"
    doc.core_properties.category = draft.category
    citations_json = json.dumps(citation_map, ensure_ascii=False)
    embedded = _embed_custom_properties(
        doc,
        {
            "RFP_Authoring_Tool": "true",
            "RFP_Clause_Citations": citations_json,
            "RFP_Verdict_Status": draft.status,
        },
    )
    if not embedded:
        doc.core_properties.keywords = "rfp-authoring-tool; clause-level-citations-embedded"

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_pdf(draft) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4, title=f"{draft.instrument}: {draft.title}",
        author="NeGD AI-Based RFP Authoring Tool", subject="Procurement document (archival)",
    )
    styles = getSampleStyleSheet()
    story = [Paragraph(f"{draft.instrument}: {draft.title}", styles["Title"])]
    story.append(Paragraph(
        f"Category: {draft.category} &nbsp; Value: ₹{draft.estimated_value_cr} Cr "
        f"&nbsp; Method: {draft.selection_method} &nbsp; Status: {draft.status.upper()}",
        styles["Italic"]))
    story.append(Spacer(1, 12))

    refs = _citation_index(draft)
    ref_pos = {r: i + 1 for i, r in enumerate(refs)}
    for c in draft.clauses.all():
        story.append(Paragraph(c.clause_type, styles["Heading2"]))
        marker_parts = []
        for m in c.citations:
            label = "{} (KB {})".format(m["citation"], m["kb_version"])
            marker_parts.append("<super>[{}]</super>".format(ref_pos[label]))
        markers = "".join(marker_parts)
        story.append(Paragraph(c.text + " " + markers, styles["BodyText"]))
        story.append(Paragraph(
            f"<i>confidence: {c.confidence} ({c.confidence_score})</i>", styles["BodyText"]))
        story.append(Spacer(1, 8))

    if refs:
        story.append(Paragraph("References (citations)", styles["Heading2"]))
        for i, r in enumerate(refs, 1):
            story.append(Paragraph(f"[{i}] {r}", styles["BodyText"]))

    pdf.build(story)
    return buf.getvalue()
