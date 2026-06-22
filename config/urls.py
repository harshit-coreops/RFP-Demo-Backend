from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.knowledge.urls")),
    path("api/", include("apps.drafting.urls")),
    path("api/", include("apps.compliance.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.exporting.urls")),
    path("api/", include("apps.review.urls")),
    path("api/", include("apps.similarity.urls")),
    path("api/", include("apps.observability.urls")),
]
