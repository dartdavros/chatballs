from django.urls import include, path
from rest_framework.schemas import get_schema_view

from hub_platform.identity.demo_views import DemoMediaView
from hub_platform.webchat.views import WidgetLoaderView

urlpatterns = [
    path("chat-widget.js", WidgetLoaderView.as_view(), name="chat-widget-loader"),
    path(
        "api/v1/schema/",
        get_schema_view(title="Chatballs API", version="0.1.0"),
        name="openapi-schema",
    ),
    path("api/v1/auth/", include("hub_platform.identity.auth_urls")),
    path("api/v1/setup/", include("hub_platform.identity.setup_urls")),
    path(
        "api/v1/demo-media/avatars/<str:name>",
        DemoMediaView.as_view(),
        name="demo-media",
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/company/",
        include("hub_platform.identity.company_urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/company/",
        include("hub_platform.products.urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/employees/",
        include("hub_platform.identity.employee_urls"),
    ),
    path("api/v1/organizations/<uuid:organization_public_id>/ai/", include("hub_platform.ai.urls")),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/agents/",
        include("hub_platform.ai.agent_card_urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/integrations/",
        include("hub_platform.integrations.urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/conversations/",
        include("hub_platform.conversations.urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/notifications/",
        include("hub_platform.notifications.urls"),
    ),
    path(
        "api/v1/organizations/<uuid:organization_public_id>/support/",
        include("hub_platform.support.urls"),
    ),
    path("api/v1/organizations/<uuid:organization_public_id>/calls/", include("hub_platform.calls.urls")),
    path("api/v1/webchat/", include("hub_platform.webchat.urls")),
    path("api/v1/health/", include("hub_platform.health.urls")),
    path("api/v1/ai/", include("hub_platform.ai.public_urls")),
    path("api/v1/support/", include("hub_platform.support.public_urls")),
    path("api/v1/help/", include("hub_platform.support_portals.public_urls")),
    path("api/v1/calls/", include("hub_platform.calls.public_urls")),
]
