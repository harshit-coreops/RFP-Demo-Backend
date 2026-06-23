"""Seed the standard clause library — the fixed *format* of an Indian govt RFP.

These are the sections that are identical across tenders (boilerplate) or whose
text is fixed with a few computed numbers (parameterized). They are inserted
verbatim by generation.generate_section(), bypassing RAG. The text below is
representative GFR/CVC-aligned demo content, mirroring the style of seed_kb.py.
"""
from django.core.management.base import BaseCommand

from apps.drafting.models import BoilerplateClause

VERSION = "v2026.06"

CLAUSES = [
    # ----------------------------- boilerplate ----------------------------
    {
        "clause_type": "Disclaimer", "kind": "boilerplate",
        "framework": "Standard", "citation": "Standard RFP Disclaimer",
        "heading": "Disclaimer",
        "description": "Verbatim legal disclaimer; identical across all tenders.",
        "body": (
            "This Request for Proposal (RFP) is issued by the Purchaser solely to "
            "assist prospective bidders in formulating their proposals. It does not "
            "purport to contain all the information each bidder may require. The "
            "information is provided on an \"as-is\" basis without any warranty, "
            "express or implied, as to its accuracy or completeness. The Purchaser, "
            "its employees and advisers accept no liability of any nature, whether "
            "in contract, tort or otherwise, for any loss or damage arising from the "
            "use of this document. The Purchaser reserves the right to amend, modify "
            "or withdraw this RFP, or to reject any or all proposals, at any stage "
            "without assigning any reason and without any liability whatsoever."
        ),
    },
    {
        "clause_type": "Definitions", "kind": "boilerplate",
        "framework": "Standard", "citation": "Definitions & Abbreviations",
        "heading": "Definitions and Abbreviations",
        "description": "Standard glossary of defined terms.",
        "body": (
            "In this document, unless the context otherwise requires: \"Purchaser\" "
            "means the procuring entity issuing this RFP; \"Bidder\" means any entity "
            "submitting a proposal in response to this RFP; \"Successful Bidder\" "
            "means the bidder selected for award of the contract; \"Contract\" means "
            "the agreement executed between the Purchaser and the Successful Bidder; "
            "\"Day\" means a calendar day; \"GFR\" means the General Financial Rules, "
            "2017; \"EMD\" means Earnest Money Deposit (Bid Security); \"PBG\" means "
            "Performance Bank Guarantee; \"SLA\" means Service Level Agreement; "
            "\"GCC\"/\"SCC\" mean the General/Special Conditions of Contract."
        ),
    },
    {
        "clause_type": "ITB", "kind": "boilerplate",
        "framework": "GFR", "citation": "Instructions to Bidders (GFR 2017)",
        "heading": "Instructions to Bidders (ITB)",
        "description": "Standard bid-process mechanics.",
        "body": (
            "Bids shall be submitted online through the Central Public Procurement "
            "(CPP) Portal / GeM in the prescribed two-cover system comprising a "
            "Technical Bid and a Financial Bid, digitally signed with a valid Class-III "
            "Digital Signature Certificate. Bids received after the notified deadline "
            "shall not be accepted. Bidders shall bear all costs associated with the "
            "preparation and submission of their bids. Any bid not accompanied by the "
            "requisite Bid Security and mandatory documents is liable to be rejected "
            "as non-responsive. Conditional bids shall not be entertained. The "
            "Purchaser may seek clarifications without altering the substance of the "
            "bid. Canvassing in any form shall render the bid liable to rejection."
        ),
    },
    {
        "clause_type": "GCC", "kind": "boilerplate",
        "framework": "GFR", "citation": "General Conditions of Contract (GFR 2017)",
        "heading": "General Conditions of Contract (GCC)",
        "description": "Standard contract terms.",
        "body": (
            "The Contract shall be governed by these General Conditions read with the "
            "Special Conditions of Contract. The Successful Bidder shall perform the "
            "Contract with due diligence and in accordance with sound professional and "
            "industry standards. Title and risk shall pass to the Purchaser on "
            "acceptance. The Purchaser may, by written notice, make changes within the "
            "general scope of the Contract, with equitable adjustment of price and "
            "schedule. Payments shall be made against verified deliverables. The "
            "Contractor shall not assign or sub-contract the whole or any part of the "
            "Contract without the prior written consent of the Purchaser. Applicable "
            "taxes shall be borne as per prevailing law."
        ),
    },
    {
        "clause_type": "Integrity Pact", "kind": "boilerplate",
        "framework": "CVC", "citation": "CVC Integrity Pact (OM No. 008/CRD/013)",
        "heading": "Integrity Pact",
        "description": "CVC standard Integrity Pact pro-forma; mandatory ≥ ₹5 Cr.",
        "body": (
            "In accordance with Central Vigilance Commission guidelines, the Bidder "
            "and the Purchaser hereby commit to an Integrity Pact. Neither party shall, "
            "directly or through any agent, offer, demand or accept any bribe, "
            "inducement or undue advantage to influence the procurement. The Bidder "
            "undertakes not to enter into any collusion, price-fixing or cartelisation "
            "with other bidders, and to disclose any payments made to agents or "
            "intermediaries. Breach of this Pact shall entitle the Purchaser to "
            "exclude the Bidder, forfeit the Bid/Performance Security, and refer the "
            "matter for action through the appointed Independent External Monitor(s)."
        ),
    },
    {
        "clause_type": "Make in India", "kind": "boilerplate",
        "framework": "PPP-MII", "citation": "Public Procurement (Preference to Make in India) Order, 2017",
        "heading": "Preference to Make in India",
        "description": "Standard local-content preference clause.",
        "body": (
            "This procurement is subject to the Public Procurement (Preference to Make "
            "in India) Order, 2017, as amended, and the relevant administrative "
            "Ministry's notifications thereunder. Purchase preference shall be "
            "extended to 'Class-I Local Suppliers' meeting the minimum local content "
            "threshold notified for the relevant item. Bidders shall self-certify the "
            "local content and the location(s) of value addition in the prescribed "
            "format. False declarations shall attract action including debarment. "
            "'Class-II Local Suppliers' and 'Non-Local Suppliers' shall be treated as "
            "per the order in force on the bid-submission date."
        ),
    },
    {
        "clause_type": "MSE Preference", "kind": "boilerplate",
        "framework": "MSE", "citation": "Public Procurement Policy for MSEs Order, 2012",
        "heading": "Preference to Micro & Small Enterprises (MSE)",
        "description": "Standard MSE purchase-preference clause.",
        "body": (
            "Bidders registered as Micro and Small Enterprises (MSEs) with a Udyam "
            "Registration / valid recognised authority for the tendered item shall be "
            "entitled to the benefits of the Public Procurement Policy for MSEs Order, "
            "2012, including exemption from Bid Security and tender fee, and purchase "
            "preference. Eligible MSEs quoting within the prescribed price band of the "
            "L1 price may be allowed to supply a portion of the requirement on matching "
            "L1, subject to the policy in force. Sub-targets for MSEs owned by SC/ST "
            "and women entrepreneurs shall apply as notified."
        ),
    },
    {
        "clause_type": "Force Majeure", "kind": "boilerplate",
        "framework": "GFR", "citation": "Force Majeure (Standard GCC)",
        "heading": "Force Majeure",
        "description": "Standard force majeure clause.",
        "body": (
            "Neither party shall be liable for any failure or delay in performing its "
            "obligations where such failure or delay results from an event of Force "
            "Majeure, being an event beyond the reasonable control of the affected "
            "party and not attributable to its negligence — including acts of God, "
            "war, civil disturbance, epidemic/pandemic, fire, flood, or restrictions "
            "imposed by Government. The affected party shall notify the other in "
            "writing within fifteen (15) days of the occurrence and use reasonable "
            "endeavours to mitigate its effects. If the Force Majeure condition "
            "continues beyond ninety (90) days, either party may terminate the "
            "Contract without liability for the unperformed portion."
        ),
    },
    {
        "clause_type": "Dispute Resolution", "kind": "boilerplate",
        "framework": "Standard", "citation": "Arbitration & Conciliation Act, 1996",
        "heading": "Dispute Resolution and Arbitration",
        "description": "Standard arbitration / governing-law clause.",
        "body": (
            "The parties shall attempt to settle any dispute arising out of or in "
            "connection with the Contract amicably through mutual consultation. "
            "Failing amicable settlement within thirty (30) days, the dispute shall be "
            "referred to arbitration by a sole arbitrator appointed in accordance with "
            "the Arbitration and Conciliation Act, 1996, as amended. The seat and "
            "venue of arbitration shall be as specified in the Special Conditions, the "
            "language shall be English, and the arbitral award shall be final and "
            "binding. The Contract shall be governed by and construed in accordance "
            "with the laws of India, and the courts at the notified jurisdiction shall "
            "have exclusive jurisdiction."
        ),
    },
    {
        "clause_type": "Confidentiality", "kind": "boilerplate",
        "framework": "Standard", "citation": "Confidentiality (Standard GCC)",
        "heading": "Confidentiality",
        "description": "Standard confidentiality / non-disclosure clause.",
        "body": (
            "The Contractor shall treat as confidential all data and information "
            "relating to the Contract or the Purchaser obtained in the course of "
            "performance, shall not disclose the same to any third party without prior "
            "written consent, and shall use it solely for the purpose of the Contract. "
            "This obligation shall survive the expiry or termination of the Contract. "
            "Any personal or sensitive data shall be processed in accordance with "
            "applicable data-protection law and shall not be transferred outside India "
            "except as expressly permitted by the Purchaser and the law in force."
        ),
    },
    # ---------------------------- parameterized ---------------------------
    {
        "clause_type": "NIT", "kind": "parameterized",
        "framework": "GFR", "citation": "GFR 2017, Rule 161 (Advertised Tender Enquiry)",
        "heading": "Notice Inviting Tender (NIT)",
        "description": "Fact-sheet header with computed value / EMD / validity slots.",
        "body": (
            "Online bids in the two-cover system are invited for {{title}} "
            "({{instrument}} — {{category}}). Estimated value of procurement: "
            "{{estimated_value}}. Selection method: {{selection_method}}. Bid "
            "Security (EMD): {{emd_amount}} ({{emd_percent}} of estimated value). "
            "Bids shall remain valid for {{bid_validity_days}} days from the date of "
            "bid opening. Tender documents may be downloaded from the CPP Portal / "
            "GeM. The Purchaser reserves the right to accept or reject any or all bids "
            "without assigning any reason. (Key dates — pre-bid meeting, last date and "
            "time for submission, and bid opening — are as notified in the e-portal "
            "tender schedule.)"
        ),
    },
    {
        "clause_type": "Bid Security (EMD)", "kind": "parameterized",
        "framework": "GFR", "citation": "GFR 2017, Rule 170 (Bid Security)",
        "heading": "Bid Security (Earnest Money Deposit)",
        "description": "Fixed EMD clause with computed amount (2% of value).",
        "body": (
            "To safeguard against a bidder's withdrawal or altering its bid during the "
            "bid-validity period, every bidder (other than those exempted under "
            "extant policy, e.g. registered MSEs / startups) shall furnish Bid "
            "Security of {{emd_amount}}, equal to {{emd_percent}} of the estimated "
            "value, in any of the acceptable forms (Bank Guarantee, Bid Security "
            "Declaration, or as specified). The Bid Security shall remain valid for "
            "forty-five (45) days beyond the bid-validity period of "
            "{{bid_validity_days}} days. It shall be forfeited if the bidder withdraws "
            "or modifies its bid during validity, or if the successful bidder fails to "
            "furnish the Performance Security or to execute the Contract."
        ),
    },
    {
        "clause_type": "Performance Security", "kind": "parameterized",
        "framework": "GFR", "citation": "GFR 2017, Rule 171 (Performance Security)",
        "heading": "Performance Security",
        "description": "Fixed PBG clause with computed amount (10% of value).",
        "body": (
            "The Successful Bidder shall furnish Performance Security of "
            "{{psg_amount}}, equal to {{psg_percent}} of the contract/estimated "
            "value, within the period specified in the award letter, in the form of a "
            "Bank Guarantee or other acceptable instrument from a scheduled commercial "
            "bank. The Performance Security shall remain valid for sixty (60) days "
            "beyond the date of completion of all contractual obligations, including "
            "the warranty/maintenance period. It shall be liable to forfeiture, in "
            "whole or in part, in the event of the Contractor's failure to perform its "
            "obligations under the Contract."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed the standard clause library (fixed/parameterized RFP boilerplate)."

    def handle(self, *args, **opts):
        created_n = 0
        for c in CLAUSES:
            obj, created = BoilerplateClause.objects.update_or_create(
                clause_type=c["clause_type"], version=VERSION,
                defaults={**c, "version": VERSION},
            )
            created_n += int(created)
            self.stdout.write(("＋ " if created else "↻ ") + f"{obj.clause_type} [{obj.kind}]")
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(CLAUSES)} boilerplate clauses ({created_n} new)."))
