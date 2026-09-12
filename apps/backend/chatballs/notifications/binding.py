"""Привязка сотрудников к сервисному боту уведомлений (TG/MAX).

Сервисный бот — messenger-интеграция с config["purpose"]="notifications",
НЕ привязанная к каналу продаж: входящие в него не создают контактов и
диалогов, он принимает только коды привязки и шлёт уведомления.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from chatballs.conversations import transports
from chatballs.conversations.transports.base import InboundMessage
from chatballs.i18n import customer_language, first_chosen, normalize_language, t
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.notifications.models import MessengerBinding, MessengerBindingCode

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=10)
NOTIFIER_PURPOSE = "notifications"


# База deep-link по провайдеру: и TG, и MAX поддерживают ?start=<код>.
_DEEP_LINK_BASE = {
    IntegrationProvider.TELEGRAM: "https://t.me/{username}?start={code}",
    IntegrationProvider.MAX: "https://max.ru/{username}?start={code}",
}


def notifier_integrations(context):
    qs = Integration.objects.filter(
        kind=IntegrationKind.MESSENGER,
        provider__in=(IntegrationProvider.TELEGRAM, IntegrationProvider.MAX),
        config__purpose=NOTIFIER_PURPOSE,
    ).exclude(secret="")
    return qs.filter(organization=context.organization)


def deep_link(integration: Integration, code: str) -> str:
    username = str(integration.config.get("bot_username", "")).strip().lstrip("@")
    template = _DEEP_LINK_BASE.get(integration.provider, "")
    if not username or not template:
        return ""
    return template.format(username=username, code=code)


def issue_binding_code(*, context, integration: Integration) -> MessengerBindingCode:
    if integration.organization_id != context.organization_id or context.actor_user is None:
        raise ValueError("Notifier integration is outside tenant context")
    user = context.actor_user
    # Прошлые коды пользователя для этого бота гасим — активен только последний.
    MessengerBindingCode.objects.filter(user=user, integration=integration).delete()
    return MessengerBindingCode.objects.create(
        user=user,
        integration=integration,
        code=secrets.token_hex(8),
        expires_at=timezone.now() + CODE_TTL,
    )


def _extract_code(text: str) -> str:
    # Принимаем и «/start <код>» (deep-link), и код, отправленный сообщением.
    parts = text.strip().split()
    if not parts:
        return ""
    if parts[0].lower().startswith("/start"):
        return parts[1] if len(parts) > 1 else ""
    return parts[0]


def handle_notifier_inbound(integration: Integration, inbound: InboundMessage) -> None:
    code_value = _extract_code(inbound.text)
    binding_code = (
        MessengerBindingCode.objects.select_related("user")
        .filter(
            integration=integration,
            code=code_value,
            expires_at__gte=timezone.now(),
            user__memberships__organization=integration.organization,
            user__memberships__blocked_at__isnull=True,
        )
        .distinct()
        .first()
        if code_value
        else None
    )
    if binding_code is None:
        hint = t("notifications.binding_hint", language=customer_language(integration.organization))
        transports.send_reply(integration, chat_id=inbound.chat_id, user_id=inbound.user_id, text=hint)
        return
    with transaction.atomic():
        # Уведомления идут ровно в один мессенджер: новая привязка заменяет прежние.
        MessengerBinding.objects.filter(
            user=binding_code.user,
            integration__organization=integration.organization,
        ).exclude(integration=integration).delete()
        MessengerBinding.objects.update_or_create(
            user=binding_code.user,
            integration=integration,
            defaults={"external_chat_id": inbound.chat_id or inbound.user_id},
        )
        binding_code.delete()
    # Подтверждение читает конкретный сотрудник — язык берём из его профиля.
    done = t(
        "notifications.binding_done",
        language=first_chosen(
            normalize_language(binding_code.user.ui_language),
            customer_language(integration.organization),
        ),
    )
    transports.send_reply(integration, chat_id=inbound.chat_id, user_id=inbound.user_id, text=done)


def poll_notifier_bots(context) -> int:
    """Поллинг сервисных ботов: только привязочные сообщения, без ingest."""
    total = 0
    for integration in notifier_integrations(context):
        messages, new_marker = transports.poll(integration)
        for inbound in messages:
            try:
                handle_notifier_inbound(integration, inbound)
                total += 1
            except Exception:  # pragma: no cover
                logger.exception("Notifier inbound failed for integration %s", integration.id)
        if new_marker and new_marker != integration.poll_marker:
            integration.poll_marker = new_marker
            integration.save(update_fields=["poll_marker", "updated_at"])
    return total
