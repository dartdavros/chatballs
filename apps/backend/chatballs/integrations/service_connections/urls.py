from django.urls import path

from chatballs.integrations.service_connections import oauth_views, views

# Подключаются в integrations/urls.py под «/integrations/».
urlpatterns = [
    path("service-adapters/", views.ServiceAdapterListView.as_view(), name="service-adapter-list"),
    path("services/", views.ServiceConnectionListView.as_view(), name="service-connection-list"),
    path("services/oauth/start/", oauth_views.ServiceOAuthStartView.as_view(), name="service-oauth-start"),
    path("services/oauth/<uuid:state_id>/", oauth_views.ServiceOAuthStateView.as_view(), name="service-oauth-state"),
    path("services/<int:connection_id>/", views.ServiceConnectionDetailView.as_view(), name="service-connection-detail"),
    path("services/<int:connection_id>/check/", views.ServiceConnectionCheckView.as_view(), name="service-connection-check"),
    path("services/<int:connection_id>/access/", views.ServiceConnectionAccessView.as_view(), name="service-connection-access"),
    path(
        "services/<int:connection_id>/lookups/<slug:key>/",
        views.ServiceLookupView.as_view(),
        name="service-connection-lookup",
    ),
]
