from django.urls import include, path
from rest_framework.schemas import get_schema_view

from chatballs.identity.demo_views import DemoMediaView
from chatballs.webchat.views import WidgetLoaderView

urlpatterns = [
    path("chat-widget.js", WidgetLoaderView.as_view(), name="chat-widget-loader"),
    path(
        "api/v1/schema/",
        get_schema_view(title="Chatballs API", version="0.1.0"),
        name="openapi-schema",
    ),
    path("api/v1/auth/", include("chatballs.identity.auth_urls")),
    path("api/v1/setup/", include("chatballs.identity.setup_urls")),
    path(
        "api/v1/demo-media/avatars/<str:name>",
        DemoMediaView.as_view(),
        name="demo-media",
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/company/",
        include("chatballs.identity.company_urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/employees/",
        include("chatballs.identity.employee_urls"),
    ),
    path("api/v1/organizations/<uuid:organization_public_id>/ai/", include("chatballs.ai.urls")),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/agents/",
        include("chatballs.ai.agent_card_urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/integrations/",
        include("chatballs.integrations.urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/conversations/",
        include("chatballs.conversations.urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/notifications/",
        include("chatballs.notifications.urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/support/portals/",
        include("chatballs.support_portals.urls"),
    ),
    path("api/v1/organizations/<uuid:organization_public_id>/calls/", include("chatballs.calls.urls")),
    path("api/v1/webchat/", include("chatballs.webchat.urls")),
    path("api/v1/health/", include("chatballs.health.urls")),
    path("api/v1/ai/", include("chatballs.ai.public_urls")),
    path("api/v1/help/", include("chatballs.support_portals.public_urls")),
    path("api/v1/calls/", include("chatballs.calls.public_urls")),
]
