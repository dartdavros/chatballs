"""Доставка уведомлений в мессенджеры через сервисных ботов.

Событие notifications.notification_created кладётся в outbox из notify() и
обрабатывается worker'ом: аудитория разворачивается в получателей (зеркало
selectors.visible_for), их привязки получают сообщение через транспорт бота.
Отправка best-effort: сбой одной привязки логируется и не валит событие.
"""

from __future__ import annotations

import logging

from django.conf import settings

from hub_platform.conversations import transports
from hub_platform.identity.models import EmployeeProfile, EmployeeRole
from hub_platform.notifications.models import (
    MessengerBinding,
    Notification,
    NotificationAudience,
    NotificationLevel,
)

logger = logging.getLogger(__name__)

NOTIFICATION_CREATED = "notifications.notification_created"

_LEVEL_MARK = {
    NotificationLevel.INFO: "🔔",
    NotificationLevel.SUCCESS: "✅",
    NotificationLevel.WARNING: "⚠️",
    NotificationLevel.CRITICAL: "🔴",
}


def _recipient_user_ids(notification: Notification) -> list[int]:
    if notification.audience == NotificationAudience.USER:
        return [notification.recipient_user_id] if notification.recipient_user_id else []
    profiles = EmployeeProfile.objects.filter(organization_id=notification.organization_id, blocked_at__isnull=True)
    if notification.audience == NotificationAudience.OWNER:
        # Административный уровень (ADR-HUB-0027 этап 2): OWNER и ADMIN.
        profiles = profiles.filter(role__in=(EmployeeRole.OWNER, EmployeeRole.ADMIN))
    elif notification.audience == NotificationAudience.OPERATORS:
        # Зеркало visible_for: аудиторию OPERATORS видят сотрудники и менеджеры (OWNER/ADMIN).
        profiles = profiles.filter(
            role__in=(EmployeeRole.EMPLOYEE, EmployeeRole.OWNER, EmployeeRole.ADMIN)
        )
    return list(profiles.values_list("user_id", flat=True))


def _message_text(notification: Notification) -> str:
    mark = _LEVEL_MARK.get(notification.level, "🔔")
    lines = [f"{mark} {notification.title}"]
    if notification.body:
        lines.append(notification.body)
    base_url = getattr(settings, "INTERNAL_UI_BASE_URL", "") or ""
    if base_url:
        lines.append(base_url)
    return "\n".join(lines)


def deliver_notification(notification: Notification) -> int:
    user_ids = _recipient_user_ids(notification)
    if not user_ids:
        return 0
    bindings = (
        MessengerBinding.objects.select_related("integration")
        .filter(user_id__in=user_ids, integration__organization_id=notification.organization_id)
    )
    text = _message_text(notification)
    sent = 0
    for binding in bindings:
        if notification.type not in (binding.push_types or []):
            continue
        try:
            if transports.send_reply(binding.integration, chat_id=binding.external_chat_id, user_id="", text=text):
                sent += 1
        except Exception:  # pragma: no cover
            logger.exception("Messenger delivery failed for binding %s", binding.id)
    return sent
