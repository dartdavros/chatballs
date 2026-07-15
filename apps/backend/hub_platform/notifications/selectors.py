from django.db.models import Q, QuerySet

from hub_platform.identity.policy import ResourceScope, accessible_department_ids, authorize
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
    department_ids = accessible_department_ids(profile, "conversations.view")
    operator_scope = Q(audience=NotificationAudience.OPERATORS)
    if department_ids is not None:
        operator_scope &= Q(department_id__in=department_ids)
    audience_scope = Q(audience__in=[a for a in audiences if a != NotificationAudience.OPERATORS])
    if NotificationAudience.OPERATORS in audiences or department_ids:
        audience_scope |= operator_scope
    return Notification.objects.filter(organization_id=profile.organization_id).filter(
        audience_scope | Q(audience=NotificationAudience.USER, recipient_user=user)
    )


def unread_for(context: TenantContext) -> QuerySet[Notification]:
    return visible_for(context).exclude(reads__user=context.actor_user)
