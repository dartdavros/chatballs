from datetime import timedelta

from django.utils import timezone

from hub_platform.notifications.models import (
    Notification,
    NotificationLevel,
    NotificationRead,
    NotificationType,
)
from hub_platform.notifications.selectors import unread_for

# Реестр типов: дефолтный уровень и маршрут диплинка. Новый тип события —
# одна запись здесь + вызов notify(...) из доменного сервиса.
TYPE_META: dict[str, dict] = {
    NotificationType.DIALOG_WAITING: {"level": NotificationLevel.WARNING, "route": "salesDialogs"},
    NotificationType.DIALOG_NEW_MESSAGE: {"level": NotificationLevel.INFO, "route": "salesDialogs"},
    NotificationType.PAYMENT_RECEIVED: {"level": NotificationLevel.SUCCESS, "route": "salesOrders"},
    NotificationType.PAYMENT_FAILED: {"level": NotificationLevel.CRITICAL, "route": "salesOrders"},
    NotificationType.RELEASE_PUBLISHED: {"level": NotificationLevel.SUCCESS, "route": "aiAgents"},
    NotificationType.INTEGRATION_ERROR: {"level": NotificationLevel.CRITICAL, "route": "integrations"},
    NotificationType.LIMIT_REACHED: {"level": NotificationLevel.WARNING, "route": "command"},
}


def notify(
    *,
    organization,
    type: str,
    audience: str,
    title: str,
    body: str = "",
    target_id: object = "",
    recipient_user=None,
    source_type: str = "",
    source_id: object = "",
    dedup_key: str = "",
    level: str | None = None,
) -> Notification | None:
    if dedup_key and Notification.objects.filter(
        organization=organization, dedup_key=dedup_key, created_at__gte=timezone.now() - timedelta(hours=24)
    ).exists():
        return None
    meta = TYPE_META.get(type, {})
    return Notification.objects.create(
        organization=organization,
        type=type,
        audience=audience,
        title=title,
        body=body,
        level=level or meta.get("level", NotificationLevel.INFO),
        target_route=meta.get("route", ""),
        target_id=str(target_id) if target_id else "",
        recipient_user=recipient_user,
        source_type=source_type,
        source_id=str(source_id) if source_id else "",
        dedup_key=dedup_key,
    )


def mark_read(*, user, ids: list[int] | None = None, all_unread: bool = False) -> int:
    queryset = unread_for(user)
    if not all_unread:
        queryset = queryset.filter(id__in=ids or [])
    rows = [NotificationRead(notification=n, user=user) for n in queryset]
    NotificationRead.objects.bulk_create(rows, ignore_conflicts=True)
    return len(rows)
