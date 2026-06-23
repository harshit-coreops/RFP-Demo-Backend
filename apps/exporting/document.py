"""Document intermediate representation (IR) for RFP-grade export.

A draft is composed once into an ordered list of *blocks* (this module), then
the DOCX and PDF renderers in ``builders.py`` each walk the same list. Keeping a
single block list is what stops the two output formats from drifting apart —
all structure/ordering decisions live in ``content.compose_document``; the
renderers only know how to draw each block type.

These dataclasses are pure data — no python-docx / reportlab imports here.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Cover:
    """Front cover page."""
    title: str
    subtitle: str = ""
    # ordered (label, value) rows shown in the cover fact box
    fields: list[tuple[str, str]] = field(default_factory=list)
    # free lines for the issuing authority block (name, address, contact …)
    issuer_lines: list[str] = field(default_factory=list)
    footer: str = ""


@dataclass
class TOC:
    """Table of contents placeholder. Renderers fill it from the headings."""
    title: str = "Table of Contents"


@dataclass
class Heading:
    """A numbered section/sub-section heading (e.g. number='2.1')."""
    text: str
    level: int = 1          # 1 = section, 2 = sub-section, 3 = clause
    number: str = ""        # "", "2", "2.1" — like the reference RFP
    toc: bool = True        # include in the table of contents


@dataclass
class Paragraph:
    """A body paragraph. ``markers`` are 1-based reference numbers rendered as
    superscript citation markers (carried over from the original builder)."""
    text: str
    style: str = "body"     # "body" | "italic" | "note"
    markers: list[int] = field(default_factory=list)


@dataclass
class Bullets:
    """A bullet or lettered/numbered list. ``items`` may contain a nested
    ``Bullets`` for one level of sub-points."""
    items: list = field(default_factory=list)   # list[str | Bullets]
    style: str = "bullet"   # "bullet" | "number" | "letter"


@dataclass
class Table:
    """A grid table. ``headers`` may be empty for a key/value style table
    (e.g. the Fact Sheet / Definitions). ``widths`` are optional relative
    column weights."""
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    caption: str = ""
    widths: list[float] | None = None


@dataclass
class Signature:
    """An authorized-signatory block with blank signature lines."""
    role: str = "Authorized Signatory"
    fields: list[str] = field(default_factory=lambda: [
        "Name and Title of Signatory:", "Name of Firm:", "Address:",
        "Email Address:", "Telephone / Fax:",
    ])
    note: str = ""


@dataclass
class PageBreak:
    pass


# A block is any of the above; renderers dispatch on type.
Block = (Cover | TOC | Heading | Paragraph | Bullets | Table | Signature | PageBreak)
