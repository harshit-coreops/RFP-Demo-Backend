from django.core.management.base import BaseCommand

from apps.drafting.models import Template

TEMPLATES = [
    {
        "key": "goods-open-rfp", "name": "Goods — Open Tender (RFP)",
        "instrument": "RFP", "category": "Goods", "selection_method": "L1",
        "version": "v2026.06", "recommended": True,
        "sections": ["NIT", "ITB", "BDS", "Scope of Work", "Eligibility", "Evaluation",
                     "Bid Security (EMD)", "Performance Security", "Integrity Pact",
                     "Make in India", "MSE Preference", "GCC", "SCC"],
        "description": "GFR-aligned template for goods supply with installation & support.",
    },
    {
        "key": "goods-limited-rfq", "name": "Goods — Limited Tender (RFQ)",
        "instrument": "RFQ", "category": "Goods", "selection_method": "LTE",
        "version": "v2026.06", "recommended": False,
        "sections": ["NIT", "ITB", "Eligibility", "Evaluation", "Bid Security (EMD)", "GCC"],
        "description": "Limited-tender route for standard low-value goods.",
    },
    {
        "key": "consulting-qcbs-rfp", "name": "Consulting — QCBS (RFP)",
        "instrument": "RFP", "category": "Consulting", "selection_method": "QCBS",
        "version": "v2026.06", "recommended": True,
        "sections": ["NIT", "ITB", "Terms of Reference", "Eligibility", "Evaluation (QCBS)",
                     "Integrity Pact", "GCC", "SCC"],
        "description": "Quality-and-cost-based selection of consultants.",
    },
    {
        "key": "eoi-panel", "name": "Empanelment — Expression of Interest (EOI)",
        "instrument": "EOI", "category": "Consulting", "selection_method": "",
        "version": "v2026.06", "recommended": False,
        "sections": ["NIT", "Eligibility", "Pre-Qualification", "Evaluation"],
        "description": "Market sounding / pre-qualification panel.",
    },
]


class Command(BaseCommand):
    help = "Seed the document template catalogue (Wizard step 2)."

    def handle(self, *args, **opts):
        for t in TEMPLATES:
            obj, created = Template.objects.update_or_create(key=t["key"], defaults=t)
            self.stdout.write(("＋ " if created else "↻ ") + obj.name)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(TEMPLATES)} templates."))
