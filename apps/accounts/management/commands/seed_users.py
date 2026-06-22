from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.accounts.models import (DelegationCeiling, Profile, SystemConfig,
                                   STATUS_ACTIVE, STATUS_INVITED)

USERS = [
    ("r.venkatesh", "R. Venkatesh", "r.venkatesh@negd.gov.in", "drafter", "NeGD", STATUS_ACTIVE),
    ("a.sharma", "A. Sharma", "a.sharma@negd.gov.in", "knowledge_admin", "NeGD", STATUS_ACTIVE),
    ("s.banerjee", "S. Banerjee", "s.banerjee@negd.gov.in", "system_admin", "NeGD", STATUS_ACTIVE),
    ("k.rao", "K. Rao", "k.rao@negd.gov.in", "knowledge_admin", "SeMT", STATUS_ACTIVE),
    ("p.iyer", "P. Iyer", "p.iyer@negd.gov.in", "drafter", "SeMT", STATUS_ACTIVE),
    ("m.gupta", "M. Gupta", "m.gupta@negd.gov.in", "drafter", "NeGD", STATUS_INVITED),
]

DELEGATIONS = [
    ("NeGD — Headquarters", "Director / Competent Authority", 50.0),
    ("SeMT — State e-Mission Teams", "Joint Director", 10.0),
    ("Project Divisions", "Deputy Secretary", 2.0),
]

DEMO_PASSWORD = "Demo@12345"  # all seeded users; change in production


class Command(BaseCommand):
    help = "Seed demo users/roles, delegation ceilings and the system config."

    def handle(self, *args, **opts):
        for username, name, email, role, unit, status in USERS:
            u, created = User.objects.get_or_create(username=username, defaults={"email": email})
            first, _, last = name.partition(" ")
            u.first_name, u.last_name, u.email = first, last, email
            u.set_password(DEMO_PASSWORD)
            u.is_staff = role == "system_admin"
            u.save()
            Profile.objects.update_or_create(
                user=u, defaults={"role": role, "unit": unit, "status": status})
            self.stdout.write(("＋ " if created else "↻ ") + f"{username} · {role}")

        DelegationCeiling.objects.all().delete()
        for unit, auth, cap in DELEGATIONS:
            DelegationCeiling.objects.create(unit=unit, authority=auth, ceiling_cr=cap)
        SystemConfig.get()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(USERS)} users (password '{DEMO_PASSWORD}'), "
            f"{len(DELEGATIONS)} delegations, config."))
