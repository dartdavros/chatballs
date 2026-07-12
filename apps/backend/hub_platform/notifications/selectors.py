from django.db.models import Q, QuerySet

from hub_platform.identity.permissions import is_manager
from hub_platform.notifications.models import Notification, NotificationAudience


def visible_for(user) -> QuerySet[Notification]:
    profile = getattr(user, "employee_profile", None)
    if profile is None:
        return Notification.objects.none()
    # Административный уровень (OWNER/ADMIN) видит owner-аудиторию (ADR-HUB-0027 этап 2).
    if is_manager(user):
        audiences = [NotificationAudience.ALL, NotificationAudience.OWNER, NotificationAudience.OPERATORS]
    else:
        audiences = [NotificationAudience.ALL, NotificationAudience.OPERATORS]
    return Notification.objects.filter(organization_id=profile.organization_id).filter(
        Q(audience__in=audiences) | Q(audience=NotificationAudience.USER, recipient_user=user)
    )


def unread_for(user) -> QuerySet[Notification]:
    return visible_for(user).exclude(reads__user=user)
