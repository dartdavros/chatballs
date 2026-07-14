from django.urls import include, path

urlpatterns = [
    path("api/v1/health/", include("hub_platform.health.urls")),
]
