from django.urls import path

from chatballs.platform import views

urlpatterns = [
    path(
        "organizations",
        views.OrganizationProvisionView.as_view(),
        name="platform-organizations-provision",
    ),
]
