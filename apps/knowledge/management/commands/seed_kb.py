"""Seed the knowledge base with representative procurement provisions.

NOTE: These are concise, representative extracts/paraphrases of public
procurement rules (GFR 2017, DoE manuals, MSE Order 2012, PPP-MII Order 2017,
CVC guidance) provided as demo corpus — NOT certified verbatim legal text.
In production this corpus is ingested from NeGD-provided source documents via
Workflow 3. Enough is seeded here for the Goods-RFP worked example to retrieve
genuine governing provisions with citations.
"""
from django.core.management.base import BaseCommand

from apps.llm.gateway import gateway
from apps.knowledge.models import Chunk, Document, KnowledgeSource

SOURCES = [
    {"key": "central", "label": "Central — GFR / DoE / GeM / MSE / PPP-MII",
     "framework": "GFR", "tier": "central", "version": "v2025_11"},
    {"key": "state_mh", "label": "State — Maharashtra (Acts, GRs, SoR)",
     "framework": "State", "tier": "state", "version": "v2025_09"},
]

# (source_key, citation, heading, text, tags)
CHUNKS = [
    ("central", "GFR 2017, Rule 170", "Bid Security (Earnest Money Deposit)",
     "To safeguard against a bidder's withdrawal or altering its bid during the "
     "bid validity period, Bid Security (also called Earnest Money Deposit) shall "
     "ordinarily be obtained from bidders, except those registered/exempted. The "
     "amount of bid security shall ordinarily range between two percent (2%) and "
     "five percent (5%) of the estimated value of the goods to be procured. Bid "
     "security shall be furnished in an acceptable form and shall remain valid for "
     "a period of forty-five (45) days beyond the bid validity period. In lieu of "
     "bid security, a Bid Security Declaration may be accepted.",
     ["bid security", "emd", "earnest money", "goods"]),

    ("central", "GFR 2017, Rule 171", "Performance Security",
     "Performance Security shall be obtained from the successful bidder for due "
     "performance of the contract. Performance Security shall be for an amount of "
     "three percent (3%) to ten percent (10%) of the value of the contract, as "
     "specified in the bidding document, and shall remain valid for sixty (60) "
     "days beyond the date of completion of all contractual obligations including "
     "the warranty period.",
     ["performance security", "performance guarantee", "contract"]),

    ("central", "GFR 2017, Rule 161", "Advertised Tender Enquiry",
     "Invitation to tenders by advertisement (Advertised Tender Enquiry) shall be "
     "used for procurement of goods of estimated value of twenty-five lakh rupees "
     "(₹25,00,000) and above. The advertisement shall be published on the Central "
     "Public Procurement Portal (CPPP) and the Government e-Marketplace (GeM) where "
     "applicable, ensuring adequate wide publicity and a reasonable bid submission "
     "period of not less than three weeks.",
     ["advertised tender", "publication", "cppp", "threshold", "tender method"]),

    ("central", "GFR 2017, Rule 162", "Limited Tender Enquiry",
     "Limited Tender Enquiry may ordinarily be adopted for procurement of goods of "
     "estimated value up to twenty-five lakh rupees (₹25,00,000). The demanding "
     "officer shall record reasons and ensure sufficient number of eligible "
     "suppliers are invited to ensure competition.",
     ["limited tender", "threshold", "tender method"]),

    ("central", "GFR 2017, Rule 173", "Eligibility and Non-restrictive Criteria",
     "The bidding document shall not contain conditions that are restrictive of "
     "competition or that unduly favour a particular bidder. Eligibility and "
     "qualification criteria shall be clearly stated, non-discriminatory, and "
     "commensurate with the value and nature of the procurement.",
     ["eligibility", "non-restrictive", "qualification", "competition"]),

    ("central", "CVC Integrity Pact Guidelines", "Integrity Pact",
     "For procurements of high value, an Integrity Pact shall be executed between "
     "the procuring entity and the bidders to enhance transparency and prevent "
     "corruption. The threshold for mandatory Integrity Pact is fixed by the "
     "procuring organisation; it is commonly applied to contracts valued at five "
     "crore rupees (₹5,00,00,000) and above. The Integrity Pact shall be monitored "
     "by an Independent External Monitor.",
     ["integrity pact", "cvc", "high value", "transparency", "threshold"]),

    ("central", "PPP-MII Order 2017 (DPIIT)", "Make-in-India Local Content Preference",
     "Under the Public Procurement (Preference to Make in India) Order, purchase "
     "preference shall be given to local suppliers meeting the prescribed minimum "
     "local content, ordinarily fifty percent (50%). Class-I local suppliers shall "
     "be eligible for purchase preference in procurements, subject to the margin of "
     "purchase preference and the verification of local content as prescribed.",
     ["ppp-mii", "make in india", "local content", "purchase preference"]),

    ("central", "MSE Procurement Policy Order 2012", "MSE Purchase Preference",
     "Every procuring entity shall endeavour to procure a minimum of twenty-five "
     "percent (25%) of its annual value of goods and services from Micro and Small "
     "Enterprises. Participating MSEs quoting within a price band of L1 + 15% shall "
     "be allowed to supply a portion of the requirement by bringing down their "
     "price to L1, where L1 is from a non-MSE.",
     ["mse", "msme", "purchase preference", "price preference"]),

    ("central", "DoE Manual for Procurement of Goods, Ch. 5", "Evaluation Method (QCBS/L1)",
     "The method of evaluation shall be specified in the bidding document. For "
     "procurement of goods, the Least Cost (L1) method among technically responsive "
     "bidders is ordinarily used. Where quality is a significant factor, Quality and "
     "Cost Based Selection (QCBS) may be adopted with the technical and financial "
     "weightages disclosed in advance.",
     ["evaluation", "qcbs", "l1", "selection method"]),

    ("central", "DoE Manual for Procurement of Goods, Ch. 3", "Mandatory Bidding Sections",
     "A complete bidding document for goods shall ordinarily include: Notice "
     "Inviting Tender (NIT), Instructions to Bidders (ITB), Bid Data Sheet (BDS), "
     "Scope of Work / Technical Specifications, Eligibility and Qualification "
     "Criteria, Evaluation Criteria, General Conditions of Contract (GCC), Special "
     "Conditions of Contract (SCC), and the prescribed bid forms and undertakings.",
     ["mandatory sections", "nit", "itb", "gcc", "scc", "structure"]),

    ("central", "GFR 2017, Rule 160", "Bid Validity Period",
     "The period of validity of bids shall be specified in the bidding document and "
     "shall be the minimum required to complete evaluation, obtain approvals, and "
     "issue the contract. An unduly long validity period shall be avoided.",
     ["bid validity", "validity period"]),

    ("state_mh", "Maharashtra e-Tendering GR (Finance Dept)", "State e-Procurement Norm",
     "Procurements above the prescribed threshold by State departments shall be "
     "conducted through the State's e-tendering platform. The Schedule of Rates "
     "(SoR) issued by the competent authority shall be the basis for estimating "
     "works and related procurement values.",
     ["state", "e-tendering", "schedule of rates", "maharashtra"]),
]


class Command(BaseCommand):
    help = "Seed knowledge sources and chunks (idempotent)."

    def handle(self, *args, **opts):
        Chunk.objects.all().delete()
        Document.objects.all().delete()
        KnowledgeSource.objects.all().delete()

        src_map = {}
        for s in SOURCES:
            src = KnowledgeSource.objects.create(**s)
            src_map[s["key"]] = src

        texts = [c[3] for c in CHUNKS]
        self.stdout.write(f"Embedding {len(texts)} chunks via '{gateway.active_provider}'...")
        vectors = gateway.embed(texts)

        docs = {}
        created = 0
        for (key, citation, heading, text, tags), emb in zip(CHUNKS, vectors):
            src = src_map[key]
            doc = docs.get((key, citation.split(",")[0]))
            if doc is None:
                doc = Document.objects.create(source=src, title=citation.split(",")[0])
                docs[(key, citation.split(",")[0])] = doc
            Chunk.objects.create(
                document=doc, source=src, citation=citation, heading=heading,
                text=text, tags=tags, embedding=emb,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(src_map)} sources and {created} chunks."
        ))
