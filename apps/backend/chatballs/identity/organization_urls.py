from django.urls import path

from chatballs.identity import organization_views

urlpatterns = [
    path("", organization_views.OrganizationCreateView.as_view(), name="organization-create"),
    path(
        "options/",
        organization_views.OrganizationCreateOptionsView.as_view(),
        name="organization-create-options",
    ),
]
