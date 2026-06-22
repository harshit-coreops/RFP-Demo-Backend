from django.db import models

# Suggestion lifecycle (FR: user may accept, modify, or reject each suggestion).
ST_OPEN = "open"
ST_ACCEPTED = "accepted"
ST_MODIFIED = "modified"
ST_REJECTED = "rejected"

CATEGORIES = ["Ambiguity", "Restrictive", "Compliance", "Clarity", "Structure", "Missing"]


class ReviewSession(models.Model):
    """Workflow 2 — AI-based review of a draft (existing or uploaded)."""

    draft = models.ForeignKey(
        "drafting.Draft", on_delete=models.CASCADE, null=True, blank=True,
        related_name="reviews",
    )
    title = models.CharField(max_length=256)
    instrument = models.CharField(max_length=8, blank=True)
    source_text = models.TextField(blank=True)  # when reviewing pasted/uploaded text
    status = models.CharField(max_length=16, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review: {self.title}"


class Suggestion(models.Model):
    session = models.ForeignKey(ReviewSession, on_delete=models.CASCADE, related_name="suggestions")
    target = models.CharField(max_length=128)        # clause type / section label
    category = models.CharField(max_length=24)
    severity = models.CharField(max_length=16, default="Medium")
    issue = models.TextField()                        # what's wrong
    original_text = models.TextField(blank=True)
    suggested_text = models.TextField(blank=True)
    rationale = models.TextField(blank=True)
    citation = models.CharField(max_length=256, blank=True)
    origin = models.CharField(max_length=16, default="llm")  # compliance | lint | llm
    status = models.CharField(max_length=16, default=ST_OPEN)
    final_text = models.TextField(blank=True)
    clause_id = models.IntegerField(null=True, blank=True)  # link back to a Clause

    class Meta:
        ordering = ["id"]
