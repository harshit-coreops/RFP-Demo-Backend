from django.test import TestCase

from .models import (Chunk, Document, IngestionJob, KnowledgeAlert,
                     KnowledgeSource, KnowledgeVersion)


class KnowledgeAdminTests(TestCase):
    def setUp(self):
        self.src = KnowledgeSource.objects.create(key="central", label="Central",
                                                  framework="GFR", tier="central", version="v2026.06")

    def test_ingest_produces_diffs(self):
        r = self.client.post("/api/knowledge/ingest/",
                            data={"source_key": "central", "title": "OM revising EMD",
                                  "text": "Office Memorandum revising bid security ceilings to two per cent."},
                            content_type="application/json")
        self.assertEqual(r.status_code, 201)
        diffs = r.json()["diffs"]
        self.assertTrue(any(d["type"] == "ADD" for d in diffs))

    def test_publish_bumps_version_and_alerts(self):
        before = self.src.version
        r = self.client.post(f"/api/knowledge/sources/{self.src.id}/publish/",
                            data={"title": "EMD revision"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json()["new_version"], before)
        self.assertTrue(KnowledgeVersion.objects.exists())
        self.assertTrue(KnowledgeAlert.objects.filter(resolved=False).exists())

    def test_alerts_endpoint(self):
        KnowledgeAlert.objects.create(title="x", body="y", tone="warn")
        self.assertEqual(len(self.client.get("/api/knowledge/alerts/").json()), 1)


class HealthTests(TestCase):
    def test_health_payload(self):
        h = self.client.get("/api/health/").json()
        self.assertEqual(len(h["metrics"]), 4)
        self.assertTrue(len(h["services"]) >= 4)
