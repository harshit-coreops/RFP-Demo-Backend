from django.urls import path

from . import views

urlpatterns = [
    path("knowledge/alerts/", views.alerts),
    path("knowledge/alerts/<int:alert_id>/resolve/", views.alert_resolve),
    path("knowledge/versions/", views.versions),
    path("knowledge/sources/<int:source_id>/publish/", views.publish),
    path("knowledge/sources/", views.sources),
    path("knowledge/sources/<int:source_id>/", views.source_detail),
    path("knowledge/search/", views.search),
    path("knowledge/ingest/", views.ingest),
    path("knowledge/ingest/<int:job_id>/decide/", views.ingest_decide),
]
