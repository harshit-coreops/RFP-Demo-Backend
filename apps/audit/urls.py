from django.urls import path

from . import views

urlpatterns = [
    path("drafts/<int:draft_id>/audit/", views.draft_audit),
]
