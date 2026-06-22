from django.db import models


class HistoricalDocument(models.Model):
    """A past procurement document, the corpus for similarity/reuse (§3.2.7)."""

    title = models.CharField(max_length=256)
    instrument = models.CharField(max_length=8, default="RFP")
    category = models.CharField(max_length=24, default="Goods")
    estimated_value_cr = models.FloatField(default=0)
    year = models.IntegerField(default=2025)
    summary = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    embedding = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title


class HistoricalClause(models.Model):
    """A reusable clause extracted from a past document (FR: reuse clauses)."""

    document = models.ForeignKey(HistoricalDocument, on_delete=models.CASCADE, related_name="clauses")
    clause_type = models.CharField(max_length=64)
    text = models.TextField()
    citation = models.CharField(max_length=256, blank=True)
    embedding = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.clause_type} @ {self.document.title}"
