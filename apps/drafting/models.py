from django.db import models

INSTRUMENTS = [("RFP", "RFP"), ("RFQ", "RFQ"), ("RFE", "RFE"), ("EOI", "EOI")]
CATEGORIES = [("Goods", "Goods"), ("Consulting", "Consulting"),
              ("Non-Consulting", "Non-Consulting")]
STATUS_DRAFT = "draft"
STATUS_FINAL = "final"


class Draft(models.Model):
    title = models.CharField(max_length=256)
    instrument = models.CharField(max_length=8, choices=INSTRUMENTS, default="RFP")
    category = models.CharField(max_length=24, choices=CATEGORIES, default="Goods")
    estimated_value_cr = models.FloatField(default=0)
    selection_method = models.CharField(max_length=32, blank=True, default="QCBS")
    brief = models.TextField(blank=True)
    namespaces = models.JSONField(default=list, blank=True)  # selected KB sources
    answers = models.JSONField(default=dict, blank=True)      # questionnaire answers
    status = models.CharField(max_length=16, default=STATUS_DRAFT)
    locked = models.BooleanField(default=False)   # set on finalise-and-lock export
    version = models.IntegerField(default=3)       # display version (mock starts at v3)
    template_key = models.CharField(max_length=64, blank=True)  # applied template (Wizard step 2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def spec(self) -> dict:
        return {
            "instrument": self.instrument,
            "category": self.category,
            "estimated_value_cr": self.estimated_value_cr,
            "selection_method": self.selection_method,
        }

    def __str__(self):
        return f"{self.instrument}: {self.title}"


class Template(models.Model):
    """A reusable document template (Wizard step 2). Promotes the previously
    hardcoded section sets into data so they can be catalogued and recommended."""

    key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    instrument = models.CharField(max_length=8, choices=INSTRUMENTS, default="RFP")
    category = models.CharField(max_length=24, choices=CATEGORIES, default="Goods")
    selection_method = models.CharField(max_length=32, blank=True, default="")
    version = models.CharField(max_length=32, default="v2026.06")
    sections = models.JSONField(default=list, blank=True)   # mandatory section labels
    description = models.TextField(blank=True)
    recommended = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.key})"


class BoilerplateClause(models.Model):
    """Fixed / parameterized standard text — the reusable *format* of an RFP.

    Unlike Clause, this is **not** RAG-generated. It is the standard
    legal/procedural text that is the same across virtually every tender
    (disclaimer, ITB, GCC, Integrity Pact, force majeure, arbitration, …).
    Parameterized entries carry ``{{slot}}`` placeholders that are filled
    deterministically from the Draft (e.g. EMD amount = 2% of value), so the
    expensive grounded-generation path is reserved for genuinely
    tender-specific prose (scope, eligibility, evaluation).
    """

    KIND_BOILERPLATE = "boilerplate"   # verbatim, no slots
    KIND_PARAMETERIZED = "parameterized"  # verbatim text + computed {{slots}}
    KINDS = [(KIND_BOILERPLATE, "boilerplate"), (KIND_PARAMETERIZED, "parameterized")]

    clause_type = models.CharField(max_length=64)
    kind = models.CharField(max_length=16, choices=KINDS, default=KIND_BOILERPLATE)
    framework = models.CharField(max_length=32, blank=True)     # GFR, CVC, PPP-MII, …
    citation = models.CharField(max_length=128, blank=True)     # standing source for audit
    version = models.CharField(max_length=32, default="v2026.06")
    heading = models.CharField(max_length=128, blank=True)
    body = models.TextField()                                   # may contain {{slots}}
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("clause_type", "version")]
        ordering = ["clause_type"]

    def __str__(self):
        return f"{self.clause_type} [{self.kind}] ({self.version})"


class Clause(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="clauses")
    clause_type = models.CharField(max_length=64)
    text = models.TextField(blank=True)
    citations = models.JSONField(default=list, blank=True)
    confidence = models.CharField(max_length=16, default="Low")
    confidence_score = models.FloatField(default=0.0)
    grounded = models.BooleanField(default=True)
    rationale = models.TextField(blank=True)
    model = models.CharField(max_length=64, blank=True)
    prompt_version = models.CharField(max_length=32, default="v1")
    accepted = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.clause_type} ({self.confidence})"
