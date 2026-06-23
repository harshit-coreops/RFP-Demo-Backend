"""On-screen preview renderer (the third renderer over the document IR).

The editor canvas needs to show each section exactly as it will appear in the
exported PDF/DOCX — generated clause prose *and* the static scaffolding (fact
sheet, eligibility/SLA/payment tables, bullet lists, Forms & Annexures, the
signature block). Rather than re-implement that layout in React (which would
drift from the export), this walks the very same ``compose_document(draft)``
block list the DOCX/PDF builders walk and serialises it to plain JSON.

Per the editor's "body sections only" preview, the cover page and the table of
contents are skipped here; everything else is grouped into sections so the
outline can list every section and the canvas can render them top to bottom.
"""
from __future__ import annotations

from .content import compose_document
from .document import (
    Bullets, Cover, Heading, PageBreak, Paragraph, Signature, TOC, Table,
)


def _ser_items(items: list) -> list:
    """Serialise bullet items, preserving one level of nested ``Bullets``."""
    out: list = []
    for it in items:
        if isinstance(it, Bullets):
            out.append({"type": "bullets", "style": it.style,
                        "items": _ser_items(it.items)})
        else:
            out.append({"type": "text", "text": str(it)})
    return out


def _ser_block(b) -> dict | None:
    if isinstance(b, Heading):
        return {"type": "heading", "level": b.level, "number": b.number,
                "text": b.text}
    if isinstance(b, Paragraph):
        return {"type": "paragraph", "style": b.style, "text": b.text,
                "markers": list(b.markers)}
    if isinstance(b, Bullets):
        return {"type": "bullets", "style": b.style,
                "items": _ser_items(b.items)}
    if isinstance(b, Table):
        return {"type": "table", "headers": list(b.headers),
                "rows": [list(r) for r in b.rows], "caption": b.caption,
                "widths": list(b.widths) if b.widths else None}
    if isinstance(b, Signature):
        return {"type": "signature", "role": b.role,
                "fields": list(b.fields), "note": b.note}
    return None


def build_preview(draft) -> dict:
    """Return ``{meta, sections}`` for the read-only editor preview.

    Sections are delimited by level-1 headings; a level-1 heading becomes the
    section title (not repeated as a body block), while level-2/3 headings render
    as sub-headings inside their section. Body content appearing before the first
    level-1 heading (the abbreviations table) is collected under an implicit
    "Definitions & Abbreviations" section so nothing is dropped from the outline.
    """
    sections: list = []
    current: dict | None = None
    idx = 0

    def open_section(number: str, title: str) -> None:
        nonlocal current, idx
        idx += 1
        current = {"id": f"sec-{idx}", "number": number, "title": title,
                   "blocks": []}
        sections.append(current)

    for b in compose_document(draft):
        if isinstance(b, (Cover, TOC, PageBreak)):
            continue
        if isinstance(b, Heading) and b.level == 1:
            open_section(b.number, b.text)
            continue
        if current is None:
            open_section("", "Definitions & Abbreviations")
        ser = _ser_block(b)
        if ser is not None:
            current["blocks"].append(ser)

    return {
        "meta": {
            "id": draft.id,
            "title": draft.title,
            "instrument": draft.instrument,
            "category": draft.category,
            "selection_method": draft.selection_method,
            "section_count": len(sections),
        },
        "sections": sections,
    }
