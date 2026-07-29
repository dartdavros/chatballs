from django.urls import path

from hub_platform.identity import administration_views, company_views

urlpatterns = [
    path("departments/", company_views.DepartmentListView.as_view(), name="department-list"),
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
        "administration/subscription/",
        administration_views.SubscriptionSummaryView.as_view(),
        name="organization-subscription",
    ),
    path(
        "administration/audit/",
        administration_views.AuditListView.as_view(),
        name="organization-audit",
    ),
]
