from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    IntegrationStatus,
)
from chatballs.webchat.models import WebChatWidget, WebChatWidgetStatus


def create_web_widget(
    channel,
    *,
    integration: Integration | None = None,
    name: str | None = None,
    allowed_origins: list[str] | None = None,
) -> WebChatWidget:
    integration = integration or Integration.objects.create(
        organization=channel.organization,
        kind=IntegrationKind.MESSENGER,
        provider=IntegrationProvider.WEB,
        name=name or f"Widget {channel.code}",
        channel=channel,
        status=IntegrationStatus.OK,
        is_active=True,
    )
    return WebChatWidget.objects.create(
        organization=channel.organization,
        integration=integration,
        code=f"web-{integration.id}",
        name=name or integration.name,
        status=WebChatWidgetStatus.PUBLISHED,
        allowed_origins=allowed_origins or [],
    )
