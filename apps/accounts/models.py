from django.contrib.auth.models import User
from django.db import models

# RFQ §3.3.1 — three personas.
ROLE_DRAFTER = "drafter"
ROLE_KNOWLEDGE_ADMIN = "knowledge_admin"
ROLE_SYSTEM_ADMIN = "system_admin"
ROLE_CHOICES = [
    (ROLE_DRAFTER, "Drafter"),
    (ROLE_KNOWLEDGE_ADMIN, "Knowledge Administrator"),
    (ROLE_SYSTEM_ADMIN, "System Administrator"),
]

STATUS_ACTIVE = "Active"
STATUS_INVITED = "Invited"
STATUS_SUSPENDED = "Suspended"


class Profile(models.Model):
    """RBAC + 2FA layer over the Django user (NFR-3 / FR-50)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_DRAFTER)
    unit = models.CharField(max_length=64, blank=True, default="NeGD")
    status = models.CharField(max_length=16, default=STATUS_ACTIVE)
    twofa_enabled = models.BooleanField(default=False)
    twofa_secret = models.CharField(max_length=64, blank=True)
    last_active = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class SystemConfig(models.Model):
    """Singleton platform configuration (System Console · Configuration tab)."""

    twofa_mandatory = models.BooleanField(default=True)         # FR-50
    password_min_length = models.IntegerField(default=12)
    password_rotation_days = models.IntegerField(default=90)
    session_timeout_min = models.IntegerField(default=30)
    data_residency = models.CharField(max_length=64, default="India-only · locked")  # DPDP Act 2023
    encryption = models.CharField(max_length=128, default="TLS 1.2+ in transit · AES-256 at rest")
    retention_days = models.IntegerField(default=365)

    @classmethod
    def get(cls) -> "SystemConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "SystemConfig"


class DelegationCeiling(models.Model):
    """Delegation of Financial Powers — per-unit approval ceilings that drive the
    recommendation engine + Integrity-Pact thresholds (System Console · Config)."""

    unit = models.CharField(max_length=128)
    authority = models.CharField(max_length=128)
    ceiling_cr = models.FloatField(default=0)

    class Meta:
        ordering = ["-ceiling_cr"]

    def __str__(self):
        return f"{self.unit} ≤ ₹{self.ceiling_cr} Cr"
