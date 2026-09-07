from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist

from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.webchat.models import WebChatWidget, WebChatWidgetStatus


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
        widget.name = integration.name
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
        "status": widget.status,
        "channel": (
            {
                "id": channel.id,
                "code": channel.code,
                "name": channel.name,
            }
            if channel is not None
            else None
        ),
    }
