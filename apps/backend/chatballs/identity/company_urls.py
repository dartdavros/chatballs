from django.urls import path

from chatballs.identity import administration_views, demo_views, group_views
from chatballs.integrations import feature_views
from chatballs.tenancy import storage_views

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
    path("demo/", demo_views.DemoDataView.as_view(), name="organization-demo-data"),
    path("administration/communication/", feature_views.CommunicationSettingsView.as_view(), name="communication-settings"),
    path("administration/storage/", storage_views.StorageSettingsView.as_view(), name="storage-settings"),
    path("administration/storage/check/", storage_views.StorageCheckView.as_view(), name="storage-check"),
    path("administration/storage/migrate/", storage_views.StorageMigrateView.as_view(), name="storage-migrate"),
    path(
        "administration/audit/",
        administration_views.AuditListView.as_view(),
        name="organization-audit",
    ),
]
