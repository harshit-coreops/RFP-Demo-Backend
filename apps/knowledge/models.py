from django.db import models

TIER_CENTRAL = "central"
TIER_MINISTRY = "ministry"
TIER_STATE = "state"
TIER_CHOICES = [
    (TIER_CENTRAL, "Tier 1 — Central"),
    (TIER_MINISTRY, "Tier 2 — Ministry overlay"),
    (TIER_STATE, "Tier 3 — State"),
]


class KnowledgeSource(models.Model):
    """A versioned corpus namespace (A&M Section B — KB tiering, §3.2.4)."""

    key = models.CharField(max_length=64, unique=True)   # e.g. "central"
    label = models.CharField(max_length=128)
    framework = models.CharField(max_length=64, blank=True)  # GFR, DoE, GeM...
    tier = models.CharField(max_length=16, choices=TIER_CHOICES, default=TIER_CENTRAL)
    version = models.CharField(max_length=32, default="v2025_11")

    @property
    def namespace(self) -> str:
        return f"{self.key}.{self.version}"

    def __str__(self):
        return self.namespace


class Document(models.Model):
    source = models.ForeignKey(KnowledgeSource, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=256)

    def __str__(self):
        return self.title


class Chunk(models.Model):
    """Clause-level chunk, bound to its citation and KB version. Embedding is
    stored as JSON for the SQLite dev path; the production path swaps in a
    pgvector column (USE_PGVECTOR) without touching callers."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    source = models.ForeignKey(KnowledgeSource, on_delete=models.CASCADE, related_name="chunks")
    citation = models.CharField(max_length=128)          # "GFR 2017, Rule 170"
    heading = models.CharField(max_length=256, blank=True)
    text = models.TextField()
    tags = models.JSONField(default=list, blank=True)     # applicability tags
    embedding = models.JSONField(default=list, blank=True)

    @property
    def kb_version(self) -> str:
        return self.source.namespace

    def __str__(self):
        return self.citation


class KnowledgeVersion(models.Model):
    """A published corpus version (timeline on the KB admin screen)."""

    source = models.ForeignKey(KnowledgeSource, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=32)
    title = models.CharField(max_length=256)
    published_by = models.CharField(max_length=64, default="knowledge.admin")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.source.key} {self.version}"


class KnowledgeAlert(models.Model):
    """A knowledge-base amendment notice shown on the dashboard (FR-09).

    Raised when a corpus version is published (or a high-impact OM is ingested)
    so drafters see which in-flight drafts are affected."""

    TONE_WARN = "warn"
    TONE_INFO = "info"

    title = models.CharField(max_length=256)
    body = models.TextField(blank=True)
    tone = models.CharField(max_length=8, default=TONE_WARN)
    framework = models.CharField(max_length=64, blank=True)
    action_label = models.CharField(max_length=64, default="Review impact")
    affected_count = models.IntegerField(default=0)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.title


class IngestionJob(models.Model):
    """Workflow 3 — a proposed knowledge-base update (OM/circular/guideline)
    pending Human-in-the-Loop validation (§3.2.5). Captures classification,
    duplicate detection and conflict flagging before approval."""

    ST_PENDING = "pending"
    ST_APPROVED = "approved"
    ST_REJECTED = "rejected"

    source = models.ForeignKey(KnowledgeSource, on_delete=models.CASCADE, related_name="ingestion_jobs")
    title = models.CharField(max_length=256)
    citation = models.CharField(max_length=128)
    raw_text = models.TextField()
    classified_framework = models.CharField(max_length=64, blank=True)
    classified_type = models.CharField(max_length=64, blank=True)   # OM | circular | guideline
    tags = models.JSONField(default=list, blank=True)
    embedding = models.JSONField(default=list, blank=True)
    duplicate_of = models.ForeignKey(Chunk, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    duplicate_score = models.FloatField(default=0.0)
    conflicts_with = models.ForeignKey(Chunk, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    conflict_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=16, default=ST_PENDING)
    created_chunk = models.ForeignKey(Chunk, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

