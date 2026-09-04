from django.urls import path

from hub_platform.identity import administration_views, group_views

urlpatterns = [
    path("groups/", group_views.GroupListView.as_view(), name="group-list"),
    path("groups/<int:group_id>/", group_views.GroupDetailView.as_view(), name="group-detail"),
    path(
        "administration/",
        administration_views.OrganizationSettingsView.as_view(),
        name="organization-settings",
    ),
    path(
        "administration/logo/",
        administration_views.OrganizationLogoView.as_view(),
        name="organization-logo",
    ),
    path(
        "launch-checklist/",
        administration_views.LaunchChecklistView.as_view(),
        name="launch-checklist",
    ),
    path(
        "administration/audit/",
        administration_views.AuditListView.as_view(),
        name="organization-audit",
    ),
]
