from django.db.models import Q, QuerySet

from hub_platform.identity.policy import ResourceScope, authorize
from hub_platform.notifications.models import Notification, NotificationAudience
from hub_platform.tenancy.context import TenantContext


def visible_for(context: TenantContext) -> QuerySet[Notification]:
    profile = context.membership
    if profile is None or context.actor_user is None:
        return Notification.objects.none()
    user = context.actor_user
    organization_scope = ResourceScope(profile.organization_id)
    audiences = []
    if authorize(profile, "company.view", organization_scope):
        audiences.append(NotificationAudience.ALL)
    if authorize(profile, "conversations.view", organization_scope):
        audiences.append(NotificationAudience.OPERATORS)
    if authorize(profile, "employees.manage_privileged", organization_scope):
        audiences.append(NotificationAudience.OWNER)
    return Notification.objects.filter(organization_id=profile.organization_id).filter(
        Q(audience__in=audiences)
        | Q(audience=NotificationAudience.USER, recipient_user=user)
    )


def unread_for(context: TenantContext) -> QuerySet[Notification]:
    return visible_for(context).exclude(reads__user=context.actor_user)
