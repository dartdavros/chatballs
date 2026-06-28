from hub_platform.notifications.models import Notification


def notification_payload(notification: Notification, *, unread: bool) -> dict[str, object]:
    return {
        "id": notification.id,
        "type": notification.type,
        "level": notification.level,
        "title": notification.title,
        "body": notification.body,
        "targetRoute": notification.target_route,
        "targetId": notification.target_id,
        "createdAt": notification.created_at.isoformat(),
        "unread": unread,
    }
