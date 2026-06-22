from django.db import models

# The compliance engine itself is stateless (computed on demand from the draft).
# Report snapshots are captured in the immutable audit trail (apps.audit).
# Per-finding overrides ARE persisted so the finalisation gate recomputes and
# the override survives re-runs (each finding has a stable key, engine.finding_key).


class ComplianceOverride(models.Model):
    """A reviewer's justified override of a single compliance finding (FR-30).

    Recorded against the draft + the finding's stable key. The justification is
    also written to the immutable audit trail at creation time."""

    draft = models.ForeignKey(
        "drafting.Draft", on_delete=models.CASCADE, related_name="compliance_overrides"
    )
    finding_key = models.CharField(max_length=128)
    framework = models.CharField(max_length=64, blank=True)
    rule = models.CharField(max_length=256, blank=True)
    justification = models.TextField()
    actor = models.CharField(max_length=64, default="demo.drafter")
    role = models.CharField(max_length=32, default="drafter")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("draft", "finding_key")
        ordering = ["-id"]

    def __str__(self):
        return f"override {self.finding_key} on draft {self.draft_id}"
