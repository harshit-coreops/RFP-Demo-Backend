from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.llm.gateway import gateway

from apps.accounts.identity import actor_role
from apps.drafting.models import Draft

from .ingestion import analyse, approve, compute_diffs
from .models import (Document, IngestionJob, KnowledgeAlert, KnowledgeSource,
                     KnowledgeVersion)
from .retrieval import retrieve
from .serializers import ChunkSerializer, KnowledgeSourceSerializer


def _job_dict(j: IngestionJob) -> dict:
    return {
        "id": j.id, "title": j.title, "citation": j.citation,
        "source": j.source.key, "framework": j.classified_framework,
        "type": j.classified_type, "tags": j.tags, "status": j.status,
        "duplicate_of": j.duplicate_of_id, "duplicate_score": j.duplicate_score,
        "conflicts_with": j.conflicts_with_id, "conflict_score": j.conflict_score,
        "note": j.note, "created_chunk": j.created_chunk_id,
        "preview": j.raw_text[:240], "created_at": j.created_at,
        "diffs": compute_diffs(j),
    }


def _alert_dict(a: KnowledgeAlert) -> dict:
    return {
        "id": a.id, "title": a.title, "body": a.body, "tone": a.tone,
        "framework": a.framework, "action_label": a.action_label,
        "affected_count": a.affected_count, "resolved": a.resolved,
        "created_at": a.created_at,
    }


@api_view(["GET"])
def alerts(request):
    """KB-amendment alerts for the dashboard (FR-09)."""
    qs = KnowledgeAlert.objects.filter(resolved=False)
    return Response([_alert_dict(a) for a in qs])


def _version_dict(v: KnowledgeVersion) -> dict:
    return {"id": v.id, "source": v.source.key, "version": v.version,
            "title": v.title, "by": v.published_by, "when": v.created_at}


@api_view(["GET"])
def versions(request):
    """Corpus version history timeline (KB admin sidebar)."""
    return Response([_version_dict(v) for v in KnowledgeVersion.objects.all()[:30]])


@api_view(["POST"])
def publish(request, source_id):
    """Publish a new corpus version (FR-10). Bumps the source version, records
    the version in history, and raises a dashboard alert for affected drafts."""
    source = KnowledgeSource.objects.get(id=source_id)
    actor, role = actor_role(request)
    old = source.version
    # Bump the minor revision: vYYYY.NN -> vYYYY.(NN+1), else append _rN.
    import re
    m = re.match(r"(v?\d{4})\.(\d+)$", old)
    if m:
        source.version = f"{m.group(1)}.{int(m.group(2)) + 1:02d}"
    else:
        m2 = re.search(r"_r(\d+)$", old)
        source.version = re.sub(r"_r\d+$", "", old) + f"_r{(int(m2.group(1)) + 1) if m2 else 1}"
    source.save()
    title = request.data.get("title", "Corpus version published")
    KnowledgeVersion.objects.create(source=source, version=source.version,
                                    title=title, published_by=actor)
    affected = Draft.objects.filter(status="draft").count()
    KnowledgeAlert.objects.create(
        title=f"{source.framework or source.label} — corpus updated to {source.version}",
        body=f"{title}. {old} → {source.version}. Affects {affected} in-flight draft(s).",
        tone="warn", framework=source.framework, action_label="Review impact",
        affected_count=affected)
    return Response({"source": KnowledgeSourceSerializer(source).data,
                     "old_version": old, "new_version": source.version,
                     "affected": affected})


@api_view(["POST"])
def alert_resolve(request, alert_id):
    a = KnowledgeAlert.objects.get(id=alert_id)
    a.resolved = True
    a.save()
    return Response(_alert_dict(a))


@api_view(["GET"])
def sources(request):
    """FR-08 / §3.2.5 — view available knowledge sources to select/deselect."""
    data = KnowledgeSourceSerializer(KnowledgeSource.objects.all(), many=True).data
    return Response({"active_llm_provider": gateway.active_provider, "sources": data})


@api_view(["GET"])
def source_detail(request, source_id):
    """FR-08 — drill into one knowledge source to view the actual rules it
    holds, grouped by source document, each with its citation and KB version."""
    source = KnowledgeSource.objects.get(id=source_id)
    documents = []
    for doc in Document.objects.filter(source=source).prefetch_related("chunks"):
        chunks = ChunkSerializer(doc.chunks.all(), many=True).data
        if chunks:
            documents.append({"id": doc.id, "title": doc.title, "chunks": chunks})
    return Response({
        "source": KnowledgeSourceSerializer(source).data,
        "documents": documents,
    })


@api_view(["POST"])
def search(request):
    """Inspect retrieval directly — useful in the live demo to show citations
    and relevance scores behind a clause."""
    query = request.data.get("query", "")
    namespaces = request.data.get("namespaces")
    hits = retrieve(query, namespaces=namespaces, top_k=request.data.get("top_k", 5))
    return Response(
        {
            "query": query,
            "results": [
                {
                    "chunk_id": h.chunk_id,
                    "citation": h.citation,
                    "kb_version": h.kb_version,
                    "score": h.score,
                    "text": h.text,
                }
                for h in hits
            ],
        }
    )


@api_view(["GET", "POST"])
def ingest(request):
    """Workflow 3 — submit an OM/circular for HITL ingestion, or list jobs."""
    if request.method == "POST":
        key = request.data.get("source_key", "central")
        source = KnowledgeSource.objects.get(key=key)
        job = analyse(source, request.data.get("title", "Untitled artefact"),
                      request.data.get("text", ""))
        return Response(_job_dict(job), status=201)
    status_filter = request.query_params.get("status")
    qs = IngestionJob.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    return Response([_job_dict(j) for j in qs])


@api_view(["POST"])
def ingest_decide(request, job_id):
    """HITL approve/reject an ingestion job (Knowledge Administrator)."""
    job = IngestionJob.objects.get(id=job_id)
    action = request.data.get("action")
    if action == "approve":
        approve(job)
    elif action == "reject":
        job.status = IngestionJob.ST_REJECTED
        job.note += " → Rejected by reviewer."
        job.save()
    return Response(_job_dict(job))
