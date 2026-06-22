"""Seed a small corpus of past procurement documents for the similarity and
reuse engine (representative demo data)."""
from django.core.management.base import BaseCommand

from apps.llm.gateway import gateway
from apps.similarity.models import HistoricalClause, HistoricalDocument

DOCS = [
    {
        "title": "RFP for Supply and Installation of Rack Servers (2024)",
        "instrument": "RFP", "category": "Goods", "estimated_value_cr": 12.5, "year": 2024,
        "summary": "Supply, installation and commissioning of enterprise rack servers "
                   "with 3-year warranty and onsite support for a data centre.",
        "tags": ["servers", "hardware", "data centre", "goods", "installation"],
        "clauses": [
            ("Bid Security (EMD)", "Bidders shall furnish bid security of 2% of the estimated "
             "value in the form of a bank guarantee valid for 45 days beyond bid validity.",
             "GFR 2017, Rule 170"),
            ("Eligibility Criteria", "The bidder shall be an OEM or an OEM-authorised partner "
             "with average annual turnover of at least the estimated value over the last three "
             "financial years, and at least two similar completed supplies.", "GFR 2017, Rule 173"),
        ],
    },
    {
        "title": "RFP for Procurement of Networking Switches (2025)",
        "instrument": "RFP", "category": "Goods", "estimated_value_cr": 16.0, "year": 2025,
        "summary": "Procurement of managed L3 networking switches with installation, "
                   "configuration and comprehensive warranty for office campuses.",
        "tags": ["networking", "switches", "hardware", "goods"],
        "clauses": [
            ("Performance Security", "The successful bidder shall furnish performance security "
             "of 3% of the contract value, valid 60 days beyond the warranty period.",
             "GFR 2017, Rule 171"),
            ("Make in India", "Purchase preference shall be granted to Class-I local suppliers "
             "meeting minimum 50% local content as per the PPP-MII Order.", "PPP-MII Order 2017"),
        ],
    },
    {
        "title": "RFQ for Annual Maintenance of Desktop Computers (2024)",
        "instrument": "RFQ", "category": "Non-Consulting", "estimated_value_cr": 0.8, "year": 2024,
        "summary": "Annual maintenance contract for desktops and peripherals including "
                   "preventive maintenance and break-fix support.",
        "tags": ["AMC", "maintenance", "desktops", "services"],
        "clauses": [
            ("Eligibility Criteria", "Bidders must have executed at least one AMC of similar "
             "nature in the last three years and hold a valid GST registration.", "GFR 2017, Rule 173"),
        ],
    },
    {
        "title": "RFP for Selection of System Integrator for Cloud Migration (2025)",
        "instrument": "RFP", "category": "Consulting", "estimated_value_cr": 22.0, "year": 2025,
        "summary": "Selection of a system integrator for migrating departmental applications "
                   "to a MeitY-empanelled cloud, with QCBS evaluation.",
        "tags": ["cloud", "system integrator", "consulting", "QCBS", "migration"],
        "clauses": [
            ("Evaluation Criteria", "Selection shall follow Quality and Cost Based Selection "
             "(QCBS) with technical and financial weightages of 70:30 disclosed in advance.",
             "DoE Manual (Consultancy)"),
            ("Integrity Pact", "An Integrity Pact shall be executed for this high-value "
             "procurement and monitored by an Independent External Monitor.",
             "CVC Integrity Pact Guidelines"),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed historical procurement documents + reusable clauses."

    def handle(self, *args, **opts):
        HistoricalClause.objects.all().delete()
        HistoricalDocument.objects.all().delete()

        doc_texts = [d["summary"] + " " + " ".join(d["tags"]) for d in DOCS]
        self.stdout.write(f"Embedding {len(doc_texts)} documents via '{gateway.active_provider}'...")
        doc_vecs = gateway.embed(doc_texts)

        clause_rows, clause_texts = [], []
        for d in DOCS:
            for ct, text, cite in d["clauses"]:
                clause_rows.append((d["title"], ct, text, cite))
                clause_texts.append(f"{ct}: {text}")
        clause_vecs = gateway.embed(clause_texts) if clause_texts else []

        by_title = {}
        for d, vec in zip(DOCS, doc_vecs):
            doc = HistoricalDocument.objects.create(
                title=d["title"], instrument=d["instrument"], category=d["category"],
                estimated_value_cr=d["estimated_value_cr"], year=d["year"],
                summary=d["summary"], full_text=d["summary"], tags=d["tags"], embedding=vec,
            )
            by_title[d["title"]] = doc

        for (title, ct, text, cite), vec in zip(clause_rows, clause_vecs):
            HistoricalClause.objects.create(
                document=by_title[title], clause_type=ct, text=text,
                citation=cite, embedding=vec,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(DOCS)} historical documents and {len(clause_rows)} reusable clauses."
        ))
