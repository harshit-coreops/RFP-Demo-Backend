"""Compose a draft into an RFP-grade block list (the single source of truth).

``compose_document(draft)`` returns an ordered ``list[Block]`` that both the
DOCX and PDF renderers walk. It welds three kinds of content together:

* **draft-derived** — the generated/boilerplate clause prose already on the
  draft (rendered as numbered sections with their citation markers);
* **parameterized** — Fact Sheet, EMD/PBG, Payment Milestones and financial
  tables filled from ``compute_slots(draft)`` (real value/EMD/PBG/validity);
* **static scaffolding** — cover page, abbreviations table, introduction,
  scope bullets, SLA tables, Forms & Annexures and the signature block, so the
  exported document looks like a complete government RFP for the demo.

Per the plan this is intentionally structured so individual static sections can
later be replaced by generated structured blocks without touching the renderers.
"""
from __future__ import annotations

from apps.drafting.boilerplate import compute_slots

from .document import (
    Bullets, Cover, Heading, PageBreak, Paragraph, Signature, TOC, Table,
)

ISSUER = "[Issuing Authority], Government of India"


class _Numberer:
    """Assigns section numbers (1, 2, 2.1 …) like the reference RFP."""

    def __init__(self) -> None:
        self.section = 0
        self.sub = 0

    def h1(self, text: str, toc: bool = True) -> Heading:
        self.section += 1
        self.sub = 0
        return Heading(text, level=1, number=str(self.section), toc=toc)

    def h2(self, text: str) -> Heading:
        self.sub += 1
        return Heading(text, level=2, number=f"{self.section}.{self.sub}")

    def plain(self, text: str, level: int = 1, toc: bool = True) -> Heading:
        """An unnumbered heading (front matter / annexures)."""
        return Heading(text, level=level, number="", toc=toc)


# --------------------------------------------------------------------------- #
# Citation references (carried over from the original builder).
# --------------------------------------------------------------------------- #
def _build_refs(draft):
    """Ordered, de-duplicated citation labels + their 1-based positions."""
    refs: list[str] = []
    for c in draft.clauses.all():
        for cit in c.citations:
            label = f"{cit['citation']} (KB {cit['kb_version']})"
            if label not in refs:
                refs.append(label)
    return refs, {r: i + 1 for i, r in enumerate(refs)}


def _markers_for(clause, ref_pos: dict) -> list[int]:
    out = []
    for cit in clause.citations:
        label = f"{cit['citation']} (KB {cit['kb_version']})"
        if label in ref_pos:
            out.append(ref_pos[label])
    return out


# --------------------------------------------------------------------------- #
# Front matter.
# --------------------------------------------------------------------------- #
def _cover(draft, slots) -> list:
    return [
        Cover(
            title=(f"Request for Proposal (RFP) for {draft.title}"),
            subtitle=(f"{draft.instrument} · {draft.category} Procurement · "
                      f"Selection method: {slots['selection_method']}"),
            fields=[
                ("Tender / GeM Bid No.", "[GEM/2026/B/XXXXXXX]"),
                ("Date of Issue", "[DD.MM.YYYY]"),
                ("Estimated Value", slots["estimated_value"]),
                ("Bid Validity", f"{slots['bid_validity_days']} days"),
            ],
            issuer_lines=[
                "Issued by:",
                ISSUER,
                "[Address line 1]",
                "[Address line 2]",
                "Website: [www.example.gov.in]",
            ],
            footer=("This RFP is issued subject to the terms, conditions and "
                    "disclaimers set out herein."),
        ),
        PageBreak(),
    ]


_ABBREVIATIONS = [
    ("RFP", "Request for Proposal"),
    ("NIT", "Notice Inviting Tender"),
    ("ITB", "Instructions to Bidders"),
    ("BDS", "Bid Data Sheet"),
    ("GCC / SCC", "General / Special Conditions of Contract"),
    ("GFR", "General Financial Rules, 2017"),
    ("EMD", "Earnest Money Deposit (Bid Security)"),
    ("PBG", "Performance Bank Guarantee (Performance Security)"),
    ("QCBS", "Quality and Cost Based Selection"),
    ("LCS", "Least Cost Selection"),
    ("L1", "Lowest evaluated responsive bid"),
    ("OEM", "Original Equipment Manufacturer"),
    ("MAF", "Manufacturer's Authorisation Form"),
    ("MII", "Make in India (PPP-MII Order, 2017)"),
    ("MSE", "Micro & Small Enterprise"),
    ("SLA", "Service Level Agreement"),
    ("O&M", "Operations & Maintenance"),
    ("PoA", "Power of Attorney"),
    ("UAT / FAT", "User / Functional Acceptance Testing"),
]


def _abbreviations() -> list:
    return [
        Paragraph("Unless the context otherwise requires, the following terms "
                  "and abbreviations shall carry the meanings assigned below.",
                  style="body"),
        Table(headers=["Abbreviation / Term", "Meaning"],
              rows=[list(r) for r in _ABBREVIATIONS],
              caption="Definitions & Abbreviations", widths=[1.0, 2.4]),
        PageBreak(),
    ]


def _introduction(draft, slots, num) -> list:
    blocks = [
        num.h1("Introduction"),
        Paragraph(
            f"This Request for Proposal (RFP) invites proposals from eligible "
            f"bidders for {draft.title}. The procurement is being undertaken as "
            f"a {draft.category} procurement under the {draft.instrument} "
            f"instrument, with bidder selection on a "
            f"{slots['selection_method']} basis, in accordance with the General "
            f"Financial Rules, 2017 and the procurement policies in force."),
    ]
    if (draft.brief or "").strip():
        blocks.append(Paragraph(draft.brief.strip()))
    blocks += [
        num.h2("Objectives"),
        Paragraph("The primary objectives of this procurement are:"),
        Bullets(items=[
            "Meet the functional and performance requirements set out in the "
            "Scope of Work in full.",
            "Ensure value for money through fair, transparent and competitive "
            "bidding.",
            "Engage a capable, financially sound and experienced bidder with a "
            "demonstrated delivery track record.",
            "Provide reliable post-implementation support over the contract "
            "period in line with the agreed Service Levels.",
        ]),
        num.h2("Disclaimer"),
        Paragraph(
            "This RFP is issued solely to assist prospective bidders in "
            "formulating their proposals and does not purport to contain all "
            "information a bidder may require. The information is provided on an "
            "\"as-is\" basis without warranty. The Purchaser reserves the right "
            "to amend, modify or withdraw this RFP, or to accept or reject any "
            "or all proposals, at any stage without assigning any reason and "
            "without liability whatsoever.", style="note"),
    ]
    return blocks


def _fact_sheet(draft, slots, num) -> list:
    rows = [
        ["1", "Tender / GeM Bid No.", "[GEM/2026/B/XXXXXXX] dated [DD.MM.YYYY]"],
        ["2", "Instrument / Category", f"{draft.instrument} — {draft.category}"],
        ["3", "Estimated value of procurement", slots["estimated_value"]],
        ["4", "Selection method", slots["selection_method"]],
        ["5", "Earnest Money Deposit (EMD)",
         f"{slots['emd_amount']} ({slots['emd_percent']} of estimated value)"],
        ["6", "Performance Security (PBG)",
         f"{slots['psg_amount']} ({slots['psg_percent']} of contract value)"],
        ["7", "Bid validity", f"{slots['bid_validity_days']} days from bid opening"],
        ["8", "Bid submission mode",
         "Online, two-cover system, via CPP Portal / GeM"],
        ["9", "Last date for pre-bid queries", "[As notified on the e-portal]"],
        ["10", "Last date & time for bid submission", "[As notified on the e-portal]"],
        ["11", "Date & time of bid opening", "[As notified on the e-portal]"],
        ["12", "Issuing / Contact Authority", ISSUER],
    ]
    return [
        num.h1("Fact Sheet"),
        Paragraph("The key parameters of this procurement are summarised below. "
                  "In the event of any inconsistency, the detailed clauses of "
                  "this RFP shall prevail."),
        Table(headers=["#", "Particulars", "Details"], rows=rows,
              caption="Fact Sheet", widths=[0.4, 1.6, 2.4]),
    ]


# --------------------------------------------------------------------------- #
# Per-clause rich blocks (appended after a clause's prose for known types).
# --------------------------------------------------------------------------- #
def _eligibility_table(draft, slots) -> list:
    cat = draft.category.lower()
    rows = [
        ["1", "The bidder shall be a firm registered in India under the "
         "Companies Act, 2013 (or a registered partnership / LLP / "
         "proprietorship) and in operation for at least three (3) years as on "
         "the bid-submission date.",
         "Certificate of Incorporation / Registration; PAN; GST registration."],
        ["2", "Average annual turnover of at least the threshold specified in "
         "the Bid Data Sheet over the last three financial years (2022-23, "
         "2023-24, 2024-25), with positive net worth as on 31 March 2025.",
         "Audited Balance Sheets and Profit & Loss statements; CA / Statutory "
         "Auditor certificate of turnover and net worth."],
        ["3", f"Prior experience of executing similar {cat} contracts for any "
         "Central / State Government / PSU / listed company in India during the "
         "last five (5) years.",
         "Work orders / purchase orders; completion or go-live certificates; "
         "client citation with contact details (see Forms)."],
        ["4", "Valid quality and information-security certifications as "
         "applicable (e.g., ISO 9001:2015 and ISO/IEC 27001:2022).",
         "Copies of valid certificates as on the bid-submission date."],
        ["5", "The bidder (and the OEM, where applicable) shall not be "
         "blacklisted or debarred by any Government / PSU / BFSI / listed "
         "entity in India in the last five (5) years.",
         "Non-blacklisting undertaking on stamp paper (see Forms)."],
        ["6", "Manufacturer's Authorisation Form (MAF) from the OEM for all "
         "proposed products / tools, where applicable.",
         "MAF on OEM letterhead (see Forms)."],
        ["7", "Compliance with the Public Procurement (Preference to Make in "
         "India) Order, 2017 and the land-border restriction (GFR Rule "
         "144(xi)).",
         "Self-certification of local content; land-border undertaking (see "
         "Forms)."],
    ]
    return [
        Paragraph("Bidders must meet ALL of the pre-qualification criteria "
                  "below. A bid failing any criterion shall be summarily "
                  "rejected. No consortium / sub-contracting of the whole work "
                  "is permitted."),
        Table(headers=["#", "Eligibility Requirement",
                       "Supporting Documents Required"], rows=rows,
              caption="Pre-Qualification Criteria", widths=[0.4, 2.2, 1.8]),
    ]


def _evaluation_table(draft, slots) -> list:
    method = (draft.selection_method or "QCBS").upper()
    if method == "QCBS":
        table = Table(
            headers=["Evaluation Stage", "Weightage", "Remarks"],
            rows=[
                ["Pre-qualification / eligibility", "Pass-Fail",
                 "Only compliant bids proceed to technical evaluation."],
                ["Technical evaluation (T)", "70%",
                 "Minimum technical qualifying score: 70 marks."],
                ["Financial evaluation (F)", "30%",
                 "Lowest financial bid (Fmin) scores 100; others pro-rata."],
            ],
            caption="Evaluation Methodology (QCBS)", widths=[2.0, 1.0, 2.0])
        note = ("Composite score = 0.70 × Technical Score + 0.30 × Financial "
                "Score. The bidder with the highest composite score (H1) shall "
                "be selected.")
    elif method in ("L1", "LCS", "LTE"):
        table = Table(
            headers=["Evaluation Stage", "Basis", "Remarks"],
            rows=[
                ["Pre-qualification / eligibility", "Pass-Fail",
                 "Only compliant bids proceed."],
                ["Technical evaluation", "Pass-Fail",
                 "Technically responsive bids qualify for financial opening."],
                ["Financial evaluation", "Least cost (L1)",
                 "Lowest evaluated responsive bid among qualified bidders."],
            ],
            caption=f"Evaluation Methodology ({method})", widths=[2.0, 1.2, 1.8])
        note = ("The lowest evaluated responsive bid (L1) among the technically "
                "qualified bidders shall be selected.")
    else:
        table = Table(
            headers=["Evaluation Stage", "Basis", "Remarks"],
            rows=[["Pre-qualification", "Pass-Fail", "As per eligibility."],
                  ["Technical & Financial", "As specified",
                   "As detailed in the Bid Data Sheet."]],
            caption=f"Evaluation Methodology ({method})", widths=[2.0, 1.2, 1.8])
        note = ("Selection shall be on the basis specified in the Bid Data "
                "Sheet for this procurement.")
    return [table, Paragraph(note, style="note")]


def _emd_table(draft, slots) -> list:
    return [Table(
        headers=["Particulars", "Details"],
        rows=[
            ["EMD amount", slots["emd_amount"]],
            ["As % of estimated value", slots["emd_percent"]],
            ["Acceptable forms",
             "Bank Guarantee / Bid Security Declaration / online payment "
             "(as specified in the BDS)"],
            ["Validity", f"45 days beyond the bid-validity period of "
             f"{slots['bid_validity_days']} days"],
            ["In favour of", f"{ISSUER}, payable at [location]"],
        ], caption="Bid Security (EMD) — at a glance", widths=[1.4, 3.0])]


def _psg_table(draft, slots) -> list:
    return [Table(
        headers=["Particulars", "Details"],
        rows=[
            ["Performance Security amount", slots["psg_amount"]],
            ["As % of contract value", slots["psg_percent"]],
            ["Form", "Bank Guarantee from a scheduled commercial bank"],
            ["Validity", "60 days beyond completion of all obligations, "
             "including the warranty / maintenance period"],
            ["Submission", "Within the period specified in the award letter"],
        ], caption="Performance Security (PBG) — at a glance", widths=[1.6, 2.8])]


def _itb_bullets(draft, slots) -> list:
    return [
        Paragraph("Bidders shall submit the bid documents in a properly indexed "
                  "and organised sequence. The bid comprises:"),
        Bullets(style="number", items=[
            "Part 1 — EMD / proof of exemption, Power of Attorney and "
            "Non-Blacklisting undertaking (online and sealed hard copy).",
            "Part 2 — Technical Bid (online), with cover letter, index and page "
            "numbering.",
            "Part 3 — Financial Bid (online only), strictly in the prescribed "
            "format.",
        ]),
        Paragraph("Documents uploaded on the portal must be legible, properly "
                  "scanned and free from any blur or cut-off content; "
                  "poor-quality or illegible documents may lead to rejection."),
    ]


# clause_type -> callable(draft, slots) -> list[Block] appended after prose.
_CLAUSE_EXTRAS = {
    "Eligibility Criteria": _eligibility_table,
    "Evaluation Criteria": _evaluation_table,
    "Bid Security (EMD)": _emd_table,
    "Performance Security": _psg_table,
    "ITB": _itb_bullets,
}


def _clauses(draft, slots, num, ref_pos) -> list:
    blocks: list = []
    for c in draft.clauses.all():
        # Definitions -> Abbreviations table; Disclaimer -> Introduction §1.2.
        if c.clause_type in ("Definitions", "Disclaimer"):
            continue
        blocks.append(num.h1(c.clause_type))
        text = (c.text or "").strip()
        if text:
            blocks.append(Paragraph(text, markers=_markers_for(c, ref_pos)))
        extra = _CLAUSE_EXTRAS.get(c.clause_type)
        if extra:
            blocks += extra(draft, slots)
    return blocks


# --------------------------------------------------------------------------- #
# Static scaffolding sections (Scope, SLA, Payment, Forms).
# --------------------------------------------------------------------------- #
def _scope_of_work(draft, num) -> list:
    """Added only when the draft has no Scope clause — guarantees bullet demo."""
    if any(c.clause_type == "Scope of Work" for c in draft.clauses.all()):
        return []
    return [
        num.h1("Scope of Work"),
        Paragraph("The selected bidder shall be responsible for the supply, "
                  "implementation and support of the solution described below "
                  "for the entire contract period:"),
        Bullets(items=[
            "Detailed requirement study, solution design and submission of "
            "design / project plan documents.",
            "Supply, installation, configuration, integration and commissioning "
            "of all components required to complete the solution.",
            Bullets(items=[
                "Provisioning of all required licences (perpetual / "
                "subscription) for the full contract period.",
                "Data migration / ingestion, cleansing and de-duplication "
                "where applicable.",
            ]),
            "User Acceptance Testing (UAT), training of designated users and "
            "go-live sign-off.",
            "Operations & Maintenance, including patch management, updates / "
            "upgrades and defect resolution, for the O&M period.",
        ]),
        Paragraph("All components shall carry the OEM's highest level of "
                  "enterprise support for the entire contract period, and the "
                  "solution shall comply with the applicable security and data "
                  "protection requirements."),
    ]


def _sla(draft, num) -> list:
    severity = Table(
        headers=["Severity", "Definition", "Target Resolution"],
        rows=[
            ["Severity 1", "Showstopper / major failure with no usable "
             "workaround.", "Within 60 minutes of reporting"],
            ["Severity 2", "Severe functional restriction; workarounds are "
             "time-consuming.", "Within 4 hours"],
            ["Severity 3", "Moderate functional restriction with a readily "
             "available workaround.", "Within 12 hours"],
            ["Severity 4", "Cosmetic change / query with no business impact.",
             "Within 48 hours"],
        ], caption="Incident Severity & Resolution Targets",
        widths=[0.9, 2.6, 1.4])
    penalty = Table(
        headers=["#", "Service Category", "Breach Threshold", "Penalty"],
        rows=[
            ["1", "System availability",
             "Availability below 99.9% in a calendar month",
             "0.5% of quarterly payment per hour of excess downtime"],
            ["2", "Report performance",
             "General reports > 5s / complex reports > 10s",
             "1% of quarterly payment per incident"],
            ["3", "Incident resolution", "Breach of severity-wise targets",
             "Slab-based % of quarterly billing"],
            ["4", "Root Cause Analysis (RCA)",
             "RCA not available within 5 days",
             "0.2% of quarterly payment per day"],
        ], caption="Service & Performance Penalties (O&M)",
        widths=[0.4, 1.5, 2.0, 1.6])
    return [
        num.h1("Service Level Agreement (SLA)"),
        Paragraph("The solution shall be a business-critical application. SLAs "
                  "shall be monitored on a quarterly basis; sustained breach "
                  "may invoke penalties and, beyond the prescribed cap, "
                  "termination. The maximum cumulative penalty under the SLA "
                  "shall be capped at 10% of the contract value."),
        severity,
        penalty,
    ]


def _payment_milestones(draft, slots, num) -> list:
    rows = [
        ["1", "Project kick-off and deployment of key resources", "T0 + 1 week", "0%"],
        ["2", "System study, design documents and project plan", "T0 + 5 weeks", "0%"],
        ["3", "Infrastructure setup, security audit and commissioning",
         "T0 + 10 weeks", "10%"],
        ["4", "Supply, installation and FAT of the core solution",
         "T0 + 12 weeks", "Licence cost as per terms"],
        ["5", "Data ingestion / integration and cleansing", "T0 + 20 weeks", "30%"],
        ["6", "Implementation, configuration and UAT sign-off (Go-Live)",
         "T0 + 60 weeks", "40%"],
        ["7", "Training of designated users", "Go-Live + 2 weeks", "10%"],
        ["8", "Commencement of O&M", "Go-Live + 1 month", "10%"],
    ]
    return [
        num.h1("Payment Terms & Milestones"),
        Paragraph("No advance payment shall be made. Payments shall be linked "
                  "to delivery and acceptance of each milestone and released "
                  "within 30 days of an undisputed invoice, after deduction of "
                  "applicable penalties and taxes. O&M payments are linked to "
                  "SLA compliance."),
        Table(headers=["#", "Milestone / Deliverable", "Indicative Timeline",
                       "Payment (% of Implementation Cost)"], rows=rows,
              caption="Implementation Payment Milestones",
              widths=[0.4, 2.4, 1.2, 1.4]),
        Paragraph("Post-implementation O&M charges shall be paid in equal "
                  "annual / quarterly instalments over the O&M period, subject "
                  "to satisfactory performance and SLA compliance.", style="note"),
    ]


def _forms_and_annexures(draft, slots, num) -> list:
    fin = Table(
        headers=["Sr.", "Scope of Deliverables", "Qty", "Total Amount (INR)"],
        rows=[
            ["1", "Supply of all required software / tools / licences "
             "(perpetual or subscription) to complete the solution", "Lot", "____"],
            ["2", "Implementation & customisation as per the Scope of Work", "1", "____"],
            ["3", "Operations & Maintenance for the contract period "
             "(incl. ATS / AMC)", "1", "____"],
            ["", "Total Evaluated Cost (inclusive of all taxes)", "", "____"],
        ], caption="Annexure 1 — Financial Bid (Summary)", widths=[0.5, 2.8, 0.6, 1.4])
    manpower = Table(
        headers=["Sr.", "Resource / Role", "Qty", "Unit Rate (INR)", "Total"],
        rows=[
            ["1", "Project Manager", "1", "____", "____"],
            ["2", "Business Analyst", "1", "____", "____"],
            ["3", "Technical / Domain Expert", "1", "____", "____"],
            ["4", "Developer / Engineer", "1", "____", "____"],
            ["5", "System Administrator / DBA", "1", "____", "____"],
        ], caption="Annexure 2 — Manpower Rate Card", widths=[0.5, 2.2, 0.6, 1.2, 1.2])
    return [
        PageBreak(),
        num.plain("Annexures & Forms", level=1),
        Paragraph("Bidders shall submit the following annexures and forms, duly "
                  "filled, signed and stamped by the authorised signatory. Forms "
                  "are indicative; the prescribed online formats shall prevail."),
        fin,
        manpower,
        num.plain("Form 1: Proposal Covering Letter", level=2, toc=False),
        Paragraph("We, the undersigned, having examined this RFP including all "
                  "annexures and corrigenda, hereby submit our proposal and "
                  "confirm that all information provided is true and correct, "
                  "that our bid is valid for the prescribed period, and that we "
                  "unconditionally accept all terms and conditions of this RFP."),
        Signature(role="Authorized Signatory (for and on behalf of the Bidder)"),
        num.plain("Form 2: Non-Blacklisting Undertaking", level=2, toc=False),
        Paragraph("We hereby declare that our firm is not blacklisted or "
                  "declared ineligible by any Central / State Government / PSU / "
                  "BFSI / listed entity in India as on the date of bid "
                  "submission. (To be furnished on ₹300 non-judicial stamp "
                  "paper.)"),
        Signature(role="Authorized Signatory"),
        num.plain("Form 3: Power of Attorney", level=2, toc=False),
        Paragraph("Know all men by these presents that we hereby constitute and "
                  "appoint the person named below as our attorney to sign and "
                  "submit this bid and to do all acts necessary in connection "
                  "with our proposal. (To be furnished on stamp paper of the "
                  "value required under law.)"),
        Signature(role="Authorized Signatory / Executant"),
    ]


def _references(refs, num) -> list:
    if not refs:
        return []
    return [
        PageBreak(),
        num.plain("References (Citations)", level=1),
        Paragraph("Each generated clause in this document is grounded in, and "
                  "cited to, the source(s) below (superscript markers in the "
                  "body refer to this list)."),
        Bullets(style="number",
                items=[f"{r}" for r in refs]),
    ]


def _signoff() -> list:
    return [
        PageBreak(),
        Heading("Acceptance & Signature", level=1, number="", toc=False),
        Paragraph("Signed for and on behalf of the Bidder, in token of "
                  "unconditional acceptance of all terms, conditions, "
                  "annexures and corrigenda of this RFP.", style="body"),
        Signature(role="Authorized Signatory",
                  note="(Affix company seal / stamp)"),
    ]


# --------------------------------------------------------------------------- #
def compose_document(draft) -> list:
    slots = compute_slots(draft)
    refs, ref_pos = _build_refs(draft)
    num = _Numberer()

    blocks: list = []
    blocks += _cover(draft, slots)
    blocks += _abbreviations()
    blocks.append(TOC())
    blocks.append(PageBreak())
    blocks += _introduction(draft, slots, num)
    blocks += _fact_sheet(draft, slots, num)
    blocks += _clauses(draft, slots, num, ref_pos)
    blocks += _scope_of_work(draft, num)
    blocks += _sla(draft, num)
    blocks += _payment_milestones(draft, slots, num)
    blocks += _forms_and_annexures(draft, slots, num)
    blocks += _references(refs, num)
    blocks += _signoff()
    return blocks
