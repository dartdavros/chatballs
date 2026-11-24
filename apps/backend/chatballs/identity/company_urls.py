from django.urls import path

from chatballs.identity import (
    administration_views,
    demo_views,
    group_views,
)
from chatballs.identity.demo_seed.north_wind.views import DemoShopCRMView, DemoShopView
from chatballs.integrations import feature_views

urlpatterns = [
    path("groups/", group_views.GroupListView.as_view(), name="group-list"),
    path("groups/<int:group_id>/", group_views.GroupDetailView.as_view(), name="group-detail"),
    path(
        "administration/",
        administration_views.OrganizationSettingsView.as_view(),
        name="organization-settings",
    ),
    # Настройки установки (адрес, почта, TURN, хранилище) — не свойства
    # организации: они живут на /api/v1/instance/ (identity.instance_urls).
    path(
        "administration/logo/",
        administration_views.OrganizationLogoView.as_view(),
        name="organization-logo",
    ),
    path(
        "onboarding/",
        administration_views.OnboardingView.as_view(),
        name="onboarding",
    ),
    path("demo/", demo_views.DemoDataView.as_view(), name="organization-demo-data"),
    path("demo/reinstall/", demo_views.DemoReinstallView.as_view(), name="organization-demo-reinstall"),
    path("demo/shop/<uuid:generation>/<slug:operation>/", DemoShopView.as_view(), name="organization-demo-shop"),
    path("demo/shop/<uuid:generation>/crm/<str:reference>/", DemoShopCRMView.as_view(), name="organization-demo-crm-record"),
    path("administration/communication/", feature_views.CommunicationSettingsView.as_view(), name="communication-settings"),
    path(
        "administration/audit/",
        administration_views.AuditListView.as_view(),
        name="organization-audit",
    ),
]
