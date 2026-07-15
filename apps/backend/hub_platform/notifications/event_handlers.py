from hub_platform.events.handlers import register
from hub_platform.notifications.delivery import NOTIFICATION_CREATED, deliver_notification
from hub_platform.notifications.models import Notification
from hub_platform.tenancy.context import TenantContext


@register(NOTIFICATION_CREATED)
def handle_notification_created(payload: dict, context: TenantContext | None) -> None:
    if context is None:
        raise ValueError("Notification event has no tenant context")
    notification = Notification.objects.filter(
        pk=payload.get("notificationId"), organization=context.organization
    ).first()
    if notification is not None:
        deliver_notification(notification)
