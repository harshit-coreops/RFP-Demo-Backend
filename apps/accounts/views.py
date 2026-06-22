import pyotp
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (DelegationCeiling, Profile, ROLE_CHOICES, ROLE_DRAFTER,
                     STATUS_INVITED, SystemConfig)
from .permissions import require_role, user_role

# ---------------------------------------------------------------- identity
def _me_payload(user) -> dict:
    p = getattr(user, "profile", None)
    return {
        "username": user.username, "email": user.email,
        "role": getattr(p, "role", ROLE_DRAFTER),
        "unit": getattr(p, "unit", ""), "twofa_enabled": getattr(p, "twofa_enabled", False),
        "authenticated": True,
    }


@api_view(["GET"])
def me(request):
    """Current actor. Unauthenticated demo requests are treated as a Drafter so
    the drafting workspace stays usable without a login wall; the System Console
    and KB publishing require a real authenticated session (FR-50 / NFR-3)."""
    if request.user.is_authenticated:
        return Response(_me_payload(request.user))
    return Response({"username": "demo.drafter", "role": "drafter", "unit": "NeGD",
                     "twofa_enabled": False, "authenticated": False})


@api_view(["GET"])
def roles(request):
    return Response([{"value": v, "label": l} for v, l in ROLE_CHOICES])


# ---------------------------------------------------------------- auth + 2FA
@api_view(["POST"])
def auth_login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    otp = request.data.get("otp", "")
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({"error": "Invalid username or password."}, status=401)
    prof, _ = Profile.objects.get_or_create(user=user)
    if prof.twofa_enabled:
        if not otp:
            return Response({"needs_otp": True}, status=200)
        if not pyotp.TOTP(prof.twofa_secret).verify(otp, valid_window=1):
            return Response({"error": "Invalid 2FA code."}, status=401)
    login(request, user)
    prof.last_active = timezone.now()
    prof.save(update_fields=["last_active"])
    return Response(_me_payload(user))


@api_view(["POST"])
def auth_logout(request):
    logout(request)
    return Response({"ok": True})


@api_view(["POST"])
def twofa_setup(request):
    """Begin TOTP enrolment: returns a secret + otpauth URI for an authenticator."""
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required."}, status=401)
    prof, _ = Profile.objects.get_or_create(user=request.user)
    if not prof.twofa_secret:
        prof.twofa_secret = pyotp.random_base32()
        prof.save(update_fields=["twofa_secret"])
    uri = pyotp.TOTP(prof.twofa_secret).provisioning_uri(
        name=request.user.username, issuer_name="NeGD RFP Authoring")
    return Response({"secret": prof.twofa_secret, "otpauth_uri": uri,
                     "enabled": prof.twofa_enabled})


@api_view(["POST"])
def twofa_verify(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required."}, status=401)
    prof = request.user.profile
    if not pyotp.TOTP(prof.twofa_secret or "").verify(request.data.get("otp", ""), valid_window=1):
        return Response({"error": "Invalid 2FA code."}, status=401)
    prof.twofa_enabled = True
    prof.save(update_fields=["twofa_enabled"])
    return Response({"twofa_enabled": True})


# ---------------------------------------------------------------- users (RBAC)
def _user_dict(u: User) -> dict:
    p = getattr(u, "profile", None)
    return {
        "id": u.id, "username": u.username, "email": u.email,
        "name": (u.get_full_name() or u.username),
        "role": getattr(p, "role", ROLE_DRAFTER),
        "role_label": dict(ROLE_CHOICES).get(getattr(p, "role", ROLE_DRAFTER), "Drafter"),
        "unit": getattr(p, "unit", ""), "status": getattr(p, "status", "Active"),
        "twofa": "Enabled" if getattr(p, "twofa_enabled", False) else "—",
        "last_active": p.last_active if p else None,
        "initials": "".join(w[0] for w in (u.get_full_name() or u.username).split()[:2]).upper(),
    }


@api_view(["GET", "POST"])
@require_role("system_admin")
def users(request):
    if request.method == "POST":
        d = request.data
        u = User.objects.create_user(username=d["username"], email=d.get("email", ""))
        u.set_unusable_password()
        first, _, last = (d.get("name", "")).partition(" ")
        u.first_name, u.last_name = first, last
        u.save()
        Profile.objects.create(user=u, role=d.get("role", ROLE_DRAFTER),
                               unit=d.get("unit", "NeGD"), status=STATUS_INVITED)
        return Response(_user_dict(u), status=201)
    return Response([_user_dict(u) for u in User.objects.select_related("profile").order_by("id")])


@api_view(["PATCH"])
@require_role("system_admin")
def user_detail(request, user_id):
    u = User.objects.get(id=user_id)
    prof, _ = Profile.objects.get_or_create(user=u)
    for f in ["role", "unit", "status"]:
        if f in request.data:
            setattr(prof, f, request.data[f])
    prof.save()
    return Response(_user_dict(u))


# ---------------------------------------------------------------- RBAC matrix
_PERMISSIONS = [
    {"p": "Create & edit drafts", "drafter": "✓", "knowledge_admin": "–", "system_admin": "–"},
    {"p": "Run compliance & override (justified)", "drafter": "✓", "knowledge_admin": "–", "system_admin": "–"},
    {"p": "Finalise & export (DOCX / PDF-A)", "drafter": "✓", "knowledge_admin": "–", "system_admin": "–"},
    {"p": "Ingest OM / circulars, review rule diffs", "drafter": "–", "knowledge_admin": "✓", "system_admin": "–"},
    {"p": "Publish knowledge-base versions", "drafter": "–", "knowledge_admin": "✓", "system_admin": "–"},
    {"p": "Manage users & RBAC", "drafter": "–", "knowledge_admin": "–", "system_admin": "✓"},
    {"p": "Configure Delegation of Financial Powers", "drafter": "–", "knowledge_admin": "–", "system_admin": "✓"},
    {"p": "View immutable audit logs", "drafter": "own", "knowledge_admin": "KB", "system_admin": "✓ all"},
]


@api_view(["GET"])
def permissions(request):
    return Response({"roles": [{"value": v, "label": l} for v, l in ROLE_CHOICES],
                     "matrix": _PERMISSIONS})


# ---------------------------------------------------------------- config
def _config_dict(c: SystemConfig) -> dict:
    return {
        "twofa_mandatory": c.twofa_mandatory, "password_min_length": c.password_min_length,
        "password_rotation_days": c.password_rotation_days, "session_timeout_min": c.session_timeout_min,
        "data_residency": c.data_residency, "encryption": c.encryption, "retention_days": c.retention_days,
    }


@api_view(["GET", "PATCH"])
def config(request):
    c = SystemConfig.get()
    if request.method == "PATCH":
        if user_role(request) != "system_admin":
            return Response({"error": "Requires role: system_admin."}, status=403)
        for f in ["twofa_mandatory", "password_min_length", "password_rotation_days",
                  "session_timeout_min", "retention_days"]:
            if f in request.data:
                setattr(c, f, request.data[f])
        c.save()
    return Response(_config_dict(c))


# ---------------------------------------------------------------- delegations
def _del_dict(d: DelegationCeiling) -> dict:
    return {"id": d.id, "unit": d.unit, "authority": d.authority, "ceiling_cr": d.ceiling_cr}


@api_view(["GET", "POST"])
def delegations(request):
    if request.method == "POST":
        if user_role(request) != "system_admin":
            return Response({"error": "Requires role: system_admin."}, status=403)
        d = DelegationCeiling.objects.create(
            unit=request.data["unit"], authority=request.data.get("authority", ""),
            ceiling_cr=request.data.get("ceiling_cr", 0) or 0)
        return Response(_del_dict(d), status=201)
    return Response([_del_dict(d) for d in DelegationCeiling.objects.all()])


@api_view(["PATCH", "DELETE"])
@require_role("system_admin")
def delegation_detail(request, del_id):
    d = DelegationCeiling.objects.get(id=del_id)
    if request.method == "DELETE":
        d.delete()
        return Response({"deleted": True})
    for f in ["unit", "authority", "ceiling_cr"]:
        if f in request.data:
            setattr(d, f, request.data[f])
    d.save()
    return Response(_del_dict(d))
