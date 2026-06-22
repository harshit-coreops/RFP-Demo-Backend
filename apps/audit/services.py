from .models import AuditRecord


def record(draft, action, **fields) -> AuditRecord:
    """Append an immutable, hash-chained audit entry."""
    last = AuditRecord.objects.filter(draft=draft).order_by("-id").first()
    entry = AuditRecord(draft=draft, action=action, **fields)
    entry.prev_hash = last.record_hash if last else ""
    entry.record_hash = entry.compute_hash()
    entry.save()
    return entry


def verify_chain(draft) -> dict:
    """Re-walk the chain and confirm no record was altered."""
    prev = ""
    count = 0
    for rec in AuditRecord.objects.filter(draft=draft).order_by("id"):
        if rec.prev_hash != prev or rec.record_hash != rec.compute_hash():
            return {"intact": False, "broken_at": rec.id, "verified": count}
        prev = rec.record_hash
        count += 1
    return {"intact": True, "verified": count}
