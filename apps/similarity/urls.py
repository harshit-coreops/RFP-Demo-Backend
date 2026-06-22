from django.urls import path

from . import views

urlpatterns = [
    path("similarity/documents/", views.documents),
    path("similarity/search/", views.search),
    path("similarity/reuse/", views.reuse),
]
