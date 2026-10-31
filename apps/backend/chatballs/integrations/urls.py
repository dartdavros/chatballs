from django.urls import include, path

from chatballs.integrations import views
from chatballs.integrations.address_validation import HttpAddressValidationView
from chatballs.webchat.asset_views import WidgetAssetUploadView

urlpatterns = [
    path("", views.IntegrationListView.as_view(), name="integration-list"),
    path("http/validate-address/", HttpAddressValidationView.as_view(), name="http-address-validation"),
    path("<int:integration_id>/", views.IntegrationDetailView.as_view(), name="integration-detail"),
    path("<int:integration_id>/test/", views.IntegrationTestView.as_view(), name="integration-test"),
    path(
        "<int:integration_id>/tools/refresh/",
        views.IntegrationToolsRefreshView.as_view(),
        name="integration-tools-refresh",
    ),
    path(
        "<int:integration_id>/tools/read-only/confirm/",
        views.IntegrationToolConfirmView.as_view(),
        name="integration-tool-read-only-confirm",
    ),
    path(
        "<int:integration_id>/tools/read-only/revoke/",
        views.IntegrationToolRevokeView.as_view(),
        name="integration-tool-read-only-revoke",
    ),
    path("<int:integration_id>/assets/", WidgetAssetUploadView.as_view(), name="integration-widget-assets"),
    path("", include("chatballs.integrations.service_connections.urls")),
    path("", include("chatballs.integrations.scenarios.urls")),
    path("", include("chatballs.integrations.execution.urls")),
]
