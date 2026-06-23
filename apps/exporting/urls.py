from django.urls import path

from . import views

urlpatterns = [
    path("drafts/<int:draft_id>/preview/", views.preview),
    path("drafts/<int:draft_id>/export/docx/", views.export_docx),
    path("drafts/<int:draft_id>/export/pdf/", views.export_pdf),
]
