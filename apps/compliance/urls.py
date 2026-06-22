from django.urls import path

from . import views

urlpatterns = [
    path("drafts/<int:draft_id>/compliance/validate/", views.validate),
    path("drafts/<int:draft_id>/compliance/findings/<str:finding_key>/override/",
         views.override_finding),
]
