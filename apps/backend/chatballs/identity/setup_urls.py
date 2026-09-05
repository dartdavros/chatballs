from django.urls import path

from chatballs.identity import setup_views

urlpatterns = [
    path("", setup_views.SetupStatusView.as_view(), name="setup-status"),
    path("complete/", setup_views.SetupView.as_view(), name="setup-complete"),
]
