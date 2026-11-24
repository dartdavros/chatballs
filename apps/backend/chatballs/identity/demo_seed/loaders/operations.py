"""Настройки очереди, уведомления и привязки мессенджера для демо."""

from __future__ import annotations

from datetime import timedelta

from chatballs.conversations.queue_models import policy_for
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate, moment, now
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.notifications.models import (
    MessengerBinding,
    MessengerBindingCode,
    Notification,
    NotificationAudience,
    NotificationLevel,
    NotificationRead,
    NotificationTransport,
)
from chatballs.notifications.preferences import update_preference


def load(refs: DemoRefs) -> None:
    data = manifest.load("operations", refs.language)
    current = now()
    # Пороги очереди — данные организации, а не установки: демо-организация
    # заводит их со значениями по умолчанию, как завела бы живая.
    policy_for(refs.organization)
    for item in data.get("notifications", []):
        _ensure_notification(refs, item, current)
    for item in data.get("messengerBindings", []):
        MessengerBinding.objects.get_or_create(
            user=refs.users[item["user"]],
            integration=refs.integrations[item["connection"]],
            defaults={
                "organization": refs.organization,
                "external_chat_id": item["externalChatId"],
            },
        )
        update_preference(
            organization_id=refs.organization.id,
            user_id=refs.users[item["user"]].id,
            transport=NotificationTransport.MESSENGER,
            enabled=True,
            types=item.get("pushTypes", []),
        )
    for item in data.get("messengerBindingCodes", []):
        MessengerBindingCode.objects.get_or_create(
            code=item["code"],
            defaults={
                "organization": refs.organization,
                "user": refs.users[item["user"]],
                "integration": refs.integrations[item["connection"]],
                "expires_at": current + timedelta(minutes=item.get("expiresInMinutes", 15)),
            },
        )


def _ensure_notification(refs: DemoRefs, item: dict, current) -> None:
    dedup_key = f"demo:{item['type']}:{item['title']}"
    notification, created = Notification.objects.get_or_create(
        organization=refs.organization,
        dedup_key=dedup_key,
        defaults={
            "type": item["type"],
            "level": item.get("level", NotificationLevel.INFO),
            "title": item["title"],
            "body": item.get("body", ""),
            "target_route": item.get("targetRoute", ""),
            "target_id": item.get("targetId", ""),
            "audience": item.get("audience", NotificationAudience.ALL),
            "recipient_user": refs.users.get(item.get("recipientUser")),
        },
    )
    if not created:
        return
    backdate(notification, moment(item, current) or current)
    for reader_key in item.get("readBy", []):
        user = refs.users.get(reader_key)
        if user is not None:
            NotificationRead.objects.get_or_create(
                notification=notification, user=user, defaults={"organization": refs.organization}
            )
