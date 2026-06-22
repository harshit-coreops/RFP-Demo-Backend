from django.urls import path

from . import views

urlpatterns = [
    path("reviews/", views.reviews),
    path("reviews/<int:review_id>/", views.review_detail),
    path("reviews/<int:review_id>/suggestions/<int:suggestion_id>/act/", views.act),
    path("reviews/<int:review_id>/apply/", views.apply_to_draft),
]
