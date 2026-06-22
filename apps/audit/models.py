import hashlib
import json

from django.db import models

# Action types captured in the clause audit trail (A&M Section B audit table).
ACTION_GENERATE = "generate"
ACTION_ACCEPT = "accept"
ACTION_EDIT = "edit"
ACTION_OVERRIDE = "override"
ACTION_COMPLIANCE = "compliance"
ACTION_FINALISE = "finalise"
ACTION_EXPORT = "export"


class AuditRecord(models.Model):
    """Append-only, hash-chained audit record. Each row links to the previous
    via prev_hash, so any tampering breaks the chain — making the trail
    defensible to CAG/CVC-style scrutiny (A&M Section B)."""

    draft = models.ForeignKey(
        "drafting.Draft", on_delete=models.CASCADE, related_name="audit_records"
    )
    clause_ref = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=24)
    clause_text = models.TextField(blank=True)
    citation = models.CharField(max_length=256, blank=True)
    kb_version = models.CharField(max_length=64, blank=True)
    confidence = models.CharField(max_length=16, blank=True)
    confidence_score = models.FloatField(default=0.0)
    model = models.CharField(max_length=64, blank=True)
    prompt_version = models.CharField(max_length=32, blank=True)
    actor = models.CharField(max_length=64, default="demo.drafter")
    role = models.CharField(max_length=32, default="drafter")
    justification = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    prev_hash = models.CharField(max_length=64, blank=True)
    record_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["id"]

    def compute_hash(self) -> str:
        payload = {
            "draft": self.draft_id,
            "clause_ref": self.clause_ref,
            "action": self.action,
            "clause_text": self.clause_text,
            "citation": self.citation,
            "kb_version": self.kb_version,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "actor": self.actor,
            "role": self.role,
            "justification": self.justification,
            "metadata": self.metadata,
            "prev_hash": self.prev_hash,
        }
        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()
