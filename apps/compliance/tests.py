from django.test import TestCase

from apps.drafting.models import Clause, Draft

from .engine import evaluate, finding_key


class ComplianceEngineTests(TestCase):
    def test_finding_keys_are_stable(self):
        self.assertEqual(finding_key("CVC", "CVC Integrity Pact Guidelines"),
                         finding_key("CVC", "CVC Integrity Pact Guidelines"))

    def test_missing_integrity_pact_blocks_high_value(self):
        rep = evaluate({"category": "Goods", "estimated_value_cr": 15}, [{"clause_type": "NIT"}])
        self.assertTrue(rep["finalisation_blocked"])
        self.assertTrue(any(f["framework"] == "CVC" and f["status"] == "Fail" for f in rep["findings"]))

    def test_override_clears_gate(self):
        clauses = [{"clause_type": "NIT"}]
        rep = evaluate({"category": "Goods", "estimated_value_cr": 15}, clauses)
        blocking = [f["key"] for f in rep["findings"] if f["status"] == "Fail"
                    and f["severity"] in ("Critical", "High")]
        rep2 = evaluate({"category": "Goods", "estimated_value_cr": 15}, clauses, overrides=blocking)
        self.assertFalse(rep2["finalisation_blocked"])
        self.assertEqual(rep2["summary"]["overridden"], len(blocking))


class ComplianceOverrideEndpointTests(TestCase):
    def setUp(self):
        self.d = Draft.objects.create(title="t", category="Goods", estimated_value_cr=15)
        Clause.objects.create(draft=self.d, clause_type="NIT", text="x")

    def test_override_requires_justification(self):
        rep = self.client.post(f"/api/drafts/{self.d.id}/compliance/validate/").json()
        key = next(f["key"] for f in rep["findings"] if f["status"] == "Fail")
        r = self.client.post(f"/api/drafts/{self.d.id}/compliance/findings/{key}/override/",
                             data={"justification": ""}, content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_override_flips_gate_and_audits(self):
        rep = self.client.post(f"/api/drafts/{self.d.id}/compliance/validate/").json()
        for f in [f for f in rep["findings"] if f["status"] == "Fail" and f["severity"] in ("Critical", "High")]:
            out = self.client.post(f"/api/drafts/{self.d.id}/compliance/findings/{f['key']}/override/",
                                   data={"justification": "Necessary and proportionate."},
                                   content_type="application/json").json()
        self.assertFalse(out["finalisation_blocked"])
        self.assertTrue(self.d.audit_records.filter(action="override").exists())
