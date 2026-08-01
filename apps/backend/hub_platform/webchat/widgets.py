from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from hub_platform.integrations.models import Integration, IntegrationProvider
from hub_platform.webchat.models import (
    WebChatWidget,
    WebChatWidgetMode,
    WebChatWidgetStatus,
)


def mode_for_integration(integration: Integration) -> str:
    channel = integration.channel
    if channel is None:
        return WebChatWidgetMode.ANONYMOUS
    if (
        channel.requires_authenticated_product_identity
        and not channel.allow_anonymous_sessions
    ):
        return WebChatWidgetMode.AUTHENTICATED_PRODUCT
    return WebChatWidgetMode.ANONYMOUS


def widget_for_integration(integration: Integration) -> WebChatWidget | None:
    try:
        return integration.web_chat_widget
    except ObjectDoesNotExist:
        return None


def _next_code(integration: Integration) -> str:
    base = f"web-{integration.id}"
    code = base
    suffix = 2
    while WebChatWidget.objects.filter(
        organization=integration.organization,
        code=code,
    ).exists():
        code = f"{base}-{suffix}"
        suffix += 1
    return code


def ensure_widget(integration: Integration) -> WebChatWidget | None:
    if integration.provider != IntegrationProvider.WEB:
        return None
    widget = widget_for_integration(integration)
    if integration.channel_id is None:
        if widget is not None and widget.status != WebChatWidgetStatus.DISABLED:
            widget.status = WebChatWidgetStatus.DISABLED
            widget.save(update_fields=["status", "updated_at"])
        return widget

    target_mode = mode_for_integration(integration)
    config = integration.config if isinstance(integration.config, dict) else {}
    presentation = {
        key: config[key]
        for key in ("title", "accent", "greeting", "quick_replies")
        if config.get(key) not in (None, "", [])
    }
    consent = {
        key: config[key]
        for key in ("consent_text", "consent_version")
        if config.get(key) not in (None, "")
    }
    if widget is None:
        widget = WebChatWidget(
            organization=integration.organization,
            integration=integration,
            code=_next_code(integration),
            name=integration.name,
            mode=target_mode,
            status=(
                WebChatWidgetStatus.DISABLED
                if not integration.is_active
                else WebChatWidgetStatus.DRAFT
            ),
            allowed_origins=config.get("allowed_domains", []),
            presentation_config=presentation,
            consent_config=consent,
        )
    else:
        if widget.mode != target_mode and widget.sessions.exists():
            raise ValidationError(
                {"channel": "Widget with existing sessions cannot change identity mode"}
            )
        widget.name = integration.name
        widget.mode = target_mode
        widget.allowed_origins = config.get("allowed_domains", [])
        widget.presentation_config = presentation
        widget.consent_config = consent
        widget.status = (
            WebChatWidgetStatus.DISABLED
            if not integration.is_active
            else WebChatWidgetStatus.DRAFT
        )

    widget.full_clean()
    widget.save()
    return widget


def sync_widget_check_status(integration: Integration, *, ok: bool) -> None:
    widget = widget_for_integration(integration)
    if widget is None:
        return
    widget.status = (
        WebChatWidgetStatus.PUBLISHED
        if ok and integration.is_active
        else WebChatWidgetStatus.DRAFT
    )
    widget.save(update_fields=["status", "updated_at"])


def widget_payload(widget: WebChatWidget | None) -> dict[str, object] | None:
    if widget is None:
        return None
    integration = widget.integration
    channel = integration.channel
    return {
        "id": widget.id,
        "code": widget.code,
        "publicKey": widget.public_key,
        "name": widget.name,
        "mode": widget.mode,
        "status": widget.status,
        "channel": (
            {
                "id": channel.id,
                "code": channel.code,
                "name": channel.name,
                "productId": channel.product_id,
            }
            if channel is not None
            else None
        ),
    }
