from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.me),
    path("roles/", views.roles),
    # auth + 2FA
    path("auth/login/", views.auth_login),
    path("auth/logout/", views.auth_logout),
    path("auth/2fa/setup/", views.twofa_setup),
    path("auth/2fa/verify/", views.twofa_verify),
    # admin (RBAC-enforced)
    path("users/", views.users),
    path("users/<int:user_id>/", views.user_detail),
    path("permissions/", views.permissions),
    path("config/", views.config),
    path("delegations/", views.delegations),
    path("delegations/<int:del_id>/", views.delegation_detail),
]
