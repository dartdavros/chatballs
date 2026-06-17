from django.urls import path

from hub_platform.health.views import live, ready

urlpatterns = [
    path("live/", live, name="health-live"),
    path("ready/", ready, name="health-ready"),
]
