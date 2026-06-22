"""RBAC enforcement for admin endpoints.

The drafting workflows stay open for the demo (unauthenticated → Drafter), but
the System Console + Knowledge publishing require a real authenticated user with
the right role. Use require_role() inside a view, or RoleRequired as a DRF
permission class."""
from __future__ import annotations

from functools import wraps

from rest_framework import permissions
from rest_framework.response import Response

from .models import ROLE_SYSTEM_ADMIN


def user_role(request) -> str | None:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    return getattr(getattr(user, "profile", None), "role", None)


def has_role(request, *roles) -> bool:
    role = user_role(request)
    return role is not None and role in roles


def require_role(*roles):
    """View decorator: 401 if anonymous, 403 if the role doesn't match."""
    def deco(view):
        @wraps(view)
        def wrapper(request, *a, **kw):
            role = user_role(request)
            if role is None:
                return Response({"error": "Authentication required."}, status=401)
            if role not in roles:
                return Response({"error": f"Requires role: {', '.join(roles)}."}, status=403)
            return view(request, *a, **kw)
        return wrapper
    return deco


class RoleRequired(permissions.BasePermission):
    roles: tuple = (ROLE_SYSTEM_ADMIN,)

    def has_permission(self, request, view):
        return has_role(request, *self.roles)
