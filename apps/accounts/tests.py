import pyotp
from django.contrib.auth.models import User
from django.test import TestCase

from .models import DelegationCeiling, Profile


def _make(username, role, pw="Demo@12345"):
    u = User.objects.create_user(username=username, password=pw)
    Profile.objects.create(user=u, role=role)
    return u


class RBACTests(TestCase):
    def setUp(self):
        _make("drafter1", "drafter")
        _make("admin1", "system_admin")

    def test_anon_blocked_from_users(self):
        self.assertEqual(self.client.get("/api/users/").status_code, 401)

    def test_drafter_blocked_from_admin(self):
        self.client.login(username="drafter1", password="Demo@12345")
        self.assertEqual(self.client.get("/api/users/").status_code, 403)
        self.assertEqual(self.client.patch("/api/config/",
                         data={"session_timeout_min": 15}, content_type="application/json").status_code, 403)

    def test_sysadmin_allowed(self):
        self.client.login(username="admin1", password="Demo@12345")
        self.assertEqual(self.client.get("/api/users/").status_code, 200)
        r = self.client.patch("/api/config/", data={"session_timeout_min": 45},
                              content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["session_timeout_min"], 45)

    def test_permissions_matrix(self):
        m = self.client.get("/api/permissions/").json()
        self.assertEqual(len(m["matrix"]), 8)
        self.assertEqual(len(m["roles"]), 3)


class TwoFactorTests(TestCase):
    def setUp(self):
        _make("admin2", "system_admin")

    def test_2fa_setup_verify_enforce(self):
        self.client.login(username="admin2", password="Demo@12345")
        setup = self.client.post("/api/auth/2fa/setup/").json()
        secret = setup["secret"]
        v = self.client.post("/api/auth/2fa/verify/",
                             data={"otp": pyotp.TOTP(secret).now()}, content_type="application/json")
        self.assertEqual(v.status_code, 200)
        self.client.logout()
        # login now needs OTP
        r = self.client.post("/api/auth/login/",
                            data={"username": "admin2", "password": "Demo@12345"},
                            content_type="application/json")
        self.assertTrue(r.json().get("needs_otp"))
        r2 = self.client.post("/api/auth/login/",
                             data={"username": "admin2", "password": "Demo@12345",
                                   "otp": pyotp.TOTP(secret).now()}, content_type="application/json")
        self.assertTrue(r2.json().get("authenticated"))


class DelegationTests(TestCase):
    def test_delegation_drives_recommendation_flag(self):
        DelegationCeiling.objects.create(unit="NeGD HQ", authority="Director", ceiling_cr=50)
        from apps.drafting.recommendation import recommend
        r = recommend({"category": "Goods", "estimated_value_cr": 15}, "servers with installation")
        self.assertTrue(any("Approving authority: Director" in f for f in r["flags"]))
