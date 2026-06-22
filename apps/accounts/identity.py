"""Resolve the acting (actor, role) for audit + RBAC.

For the demo slice an unauthenticated request is treated as a Drafter so the
workspace is usable without a login wall. With real auth (Phase 3) the
authenticated user + their Profile.role flow through unchanged."""
from __future__ import annotations

DEMO_ACTOR = "demo.drafter"
DEMO_ROLE = "drafter"


def actor_role(request) -> tuple[str, str]:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        role = getattr(getattr(user, "profile", None), "role", DEMO_ROLE)
        return user.username, role
    return DEMO_ACTOR, DEMO_ROLE
