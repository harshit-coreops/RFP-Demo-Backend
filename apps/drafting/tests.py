from django.test import TestCase

from .intake import classify_brief, parse_value_cr, value_band
from .models import Draft, Template
from .recommendation import recommend


class IntakeTests(TestCase):
    def test_value_parsing(self):
        self.assertEqual(parse_value_cr("estimated value ₹15 crore"), 15.0)
        self.assertEqual(parse_value_cr("about 85 lakh"), 0.85)

    def test_value_band(self):
        self.assertEqual(value_band(15), "₹5 Cr – ₹50 Cr")
        self.assertEqual(value_band(0.1), "< ₹25 Lakh")

    def test_classify_detects_goods(self):
        c = classify_brief("Supply and installation of 40 servers, value 15 crore")
        self.assertEqual(c["category"], "Goods")
        self.assertEqual(c["estimated_value_cr"], 15)


class RecommendationTests(TestCase):
    def test_goods_with_install_is_rfp_open(self):
        r = recommend({"category": "Goods", "estimated_value_cr": 15}, "servers with installation and support")
        self.assertEqual(r["instrument"], "RFP")
        self.assertEqual(r["method"], "Open Tender")
        self.assertTrue(any("Integrity Pact" in f for f in r["flags"]))

    def test_low_value_goods_is_rfq_limited(self):
        r = recommend({"category": "Goods", "estimated_value_cr": 0.1}, "supply of printers")
        self.assertEqual(r["instrument"], "RFQ")
        self.assertEqual(r["method"], "Limited Tender")


class TemplateEndpointTests(TestCase):
    def setUp(self):
        Template.objects.create(key="goods-open-rfp", name="Goods RFP", instrument="RFP",
                                category="Goods", selection_method="L1", sections=["NIT", "ITB"],
                                recommended=True)
        self.d = Draft.objects.create(title="t", category="Goods")

    def test_list_and_apply_template(self):
        lst = self.client.get("/api/templates/?category=Goods").json()
        self.assertEqual(len(lst), 1)
        r = self.client.post(f"/api/drafts/{self.d.id}/apply-template/",
                             data={"template_key": "goods-open-rfp"}, content_type="application/json")
        self.assertEqual(r.json()["template_key"], "goods-open-rfp")
        self.assertEqual(r.json()["instrument"], "RFP")


class DraftListTests(TestCase):
    def test_list_carries_compliance_summary(self):
        Draft.objects.create(title="t", category="Goods", estimated_value_cr=15)
        row = self.client.get("/api/drafts/").json()[0]
        self.assertIn("compliance", row)
        self.assertIn("updated_at", row)
