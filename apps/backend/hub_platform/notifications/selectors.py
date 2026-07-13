from django.db.models import Q, QuerySet

from hub_platform.identity.policy import ResourceScope, accessible_department_ids, authorize
from hub_platform.notifications.models import Notification, NotificationAudience


def visible_for(user) -> QuerySet[Notification]:
    profile = getattr(user, "employee_profile", None)
    if profile is None:
        return Notification.objects.none()
    organization_scope = ResourceScope(profile.organization_id)
    audiences = []
    if authorize(user, "company.view", organization_scope):
        audiences.append(NotificationAudience.ALL)
    if authorize(user, "conversations.view", organization_scope):
        audiences.append(NotificationAudience.OPERATORS)
    if authorize(user, "employees.manage_privileged", organization_scope):
        audiences.append(NotificationAudience.OWNER)
    department_ids = accessible_department_ids(user, "conversations.view")
    operator_scope = Q(audience=NotificationAudience.OPERATORS)
    if department_ids is not None:
        operator_scope &= Q(department_id__in=department_ids)
    audience_scope = Q(audience__in=[a for a in audiences if a != NotificationAudience.OPERATORS])
    if NotificationAudience.OPERATORS in audiences or department_ids:
        audience_scope |= operator_scope
    return Notification.objects.filter(organization_id=profile.organization_id).filter(
        audience_scope | Q(audience=NotificationAudience.USER, recipient_user=user)
    )


def unread_for(user) -> QuerySet[Notification]:
    return visible_for(user).exclude(reads__user=user)
