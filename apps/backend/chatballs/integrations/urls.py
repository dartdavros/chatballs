from django.urls import path

from chatballs.integrations import views

urlpatterns = [
    path("", views.IntegrationListView.as_view(), name="integration-list"),
    path("<int:integration_id>/", views.IntegrationDetailView.as_view(), name="integration-detail"),
    path("<int:integration_id>/test/", views.IntegrationTestView.as_view(), name="integration-test"),
]
