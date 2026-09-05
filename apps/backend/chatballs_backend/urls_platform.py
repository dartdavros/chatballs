from django.urls import include, path
from chatballs.support_portals.gateway_views import HelpDomainAuthorizationView

urlpatterns = [
    path("api/v1/health/", include("chatballs.health.urls")),
    path(
        "api/v1/gateway/help-domain/",
        HelpDomainAuthorizationView.as_view(),
        name="gateway-help-domain",
    ),
    path("api/v1/", include("chatballs.platform.urls")),
]
