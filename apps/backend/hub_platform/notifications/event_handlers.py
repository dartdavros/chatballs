from hub_platform.events.handlers import register
from hub_platform.notifications.delivery import NOTIFICATION_CREATED, deliver_notification
from hub_platform.notifications.models import Notification


@register(NOTIFICATION_CREATED)
def handle_notification_created(payload: dict) -> None:
    notification = Notification.objects.filter(pk=payload.get("notificationId")).first()
    if notification is not None:
        deliver_notification(notification)
