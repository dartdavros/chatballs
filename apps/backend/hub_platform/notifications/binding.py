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

from hub_platform.conversations import transports
from hub_platform.conversations.transports.base import InboundMessage
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider
from hub_platform.notifications.models import MessengerBinding, MessengerBindingCode

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=10)
NOTIFIER_PURPOSE = "notifications"

CONFIRMATION_TEXT = "Готово! Уведомления Edevs Hub подключены. Отключить можно в профиле."
HINT_TEXT = "Это сервисный бот уведомлений Edevs Hub. Чтобы подключить уведомления, откройте профиль в Hub и нажмите «Подключить»."

# База deep-link по провайдеру: и TG, и MAX поддерживают ?start=<код>.
_DEEP_LINK_BASE = {
    IntegrationProvider.TELEGRAM: "https://t.me/{username}?start={code}",
    IntegrationProvider.MAX: "https://max.ru/{username}?start={code}",
}


def notifier_integrations(organization_id: int | None = None):
    qs = Integration.objects.filter(
        kind=IntegrationKind.MESSENGER,
        provider__in=(IntegrationProvider.TELEGRAM, IntegrationProvider.MAX),
        config__purpose=NOTIFIER_PURPOSE,
    ).exclude(secret="")
    if organization_id is not None:
        qs = qs.filter(organization_id=organization_id)
    return qs


def deep_link(integration: Integration, code: str) -> str:
    username = str(integration.config.get("bot_username", "")).strip().lstrip("@")
    template = _DEEP_LINK_BASE.get(integration.provider, "")
    if not username or not template:
        return ""
    return template.format(username=username, code=code)


def issue_binding_code(*, user, integration: Integration) -> MessengerBindingCode:
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
        .filter(integration=integration, code=code_value, expires_at__gte=timezone.now())
        .first()
        if code_value
        else None
    )
    if binding_code is None:
        transports.send_reply(integration, chat_id=inbound.chat_id, user_id=inbound.user_id, text=HINT_TEXT)
        return
    with transaction.atomic():
        MessengerBinding.objects.update_or_create(
            user=binding_code.user,
            integration=integration,
            defaults={"external_chat_id": inbound.chat_id or inbound.user_id},
        )
        binding_code.delete()
    transports.send_reply(integration, chat_id=inbound.chat_id, user_id=inbound.user_id, text=CONFIRMATION_TEXT)


def poll_notifier_bots() -> int:
    """Поллинг сервисных ботов: только привязочные сообщения, без ingest."""
    total = 0
    for integration in notifier_integrations():
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
