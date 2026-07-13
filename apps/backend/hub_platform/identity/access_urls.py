from django.urls import path

from hub_platform.identity import access_views

urlpatterns = [
    path("", access_views.AccessProfileListCreateView.as_view(), name="access-profile-list"),
    path("capabilities/", access_views.CapabilityRegistryView.as_view(), name="capability-registry"),
    path("<int:profile_id>/", access_views.AccessProfileDetailView.as_view(), name="access-profile-detail"),
]
