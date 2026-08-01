from hub_platform.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    IntegrationStatus,
)
from hub_platform.webchat.models import (
    WebChatWidget,
    WebChatWidgetMode,
    WebChatWidgetStatus,
)


def create_web_widget(
    channel,
    *,
    integration: Integration | None = None,
    name: str | None = None,
    mode: str | None = None,
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
    resolved_mode = mode or (
        WebChatWidgetMode.AUTHENTICATED_PRODUCT
        if channel.requires_authenticated_product_identity
        else WebChatWidgetMode.ANONYMOUS
    )
    return WebChatWidget.objects.create(
        organization=channel.organization,
        integration=integration,
        code=f"web-{integration.id}",
        name=name or integration.name,
        mode=resolved_mode,
        status=WebChatWidgetStatus.PUBLISHED,
        allowed_origins=allowed_origins or [],
    )
