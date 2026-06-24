from django.urls import path

from . import views

urlpatterns = [
    path("drafts/", views.drafts),
    path("drafts/classify/", views.classify),
    path("templates/", views.templates),
    path("sections/", views.sections),
    path("drafts/<int:draft_id>/", views.draft_detail),
    path("drafts/<int:draft_id>/classify/", views.classify),
    path("drafts/<int:draft_id>/recommendation/", views.recommendation),
    path("drafts/<int:draft_id>/apply-template/", views.apply_template),
    path("drafts/<int:draft_id>/questionnaire/", views.questionnaire),
    path("drafts/<int:draft_id>/generate/", views.generate),
    path("drafts/<int:draft_id>/clauses/<int:clause_id>/accept/", views.accept_clause),
    path("drafts/<int:draft_id>/suggestions/", views.draft_suggestions),
    path("drafts/<int:draft_id>/finalise/", views.finalise),
]
