"""Public employee selectors, including availability and pending invitations."""

from rest_framework.exceptions import NotFound, PermissionDenied

from chatballs.api.pagination import page_payload, paginate
from chatballs.i18n import t
from chatballs.identity.employee_availability import employee_availability
from chatballs.identity.employee_invitation_queries import pending_invitations_payload
from chatballs.identity.employee_selectors import employees_for
from chatballs.identity.employee_support import employee_payload, profile_for
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.policy import has_capability_any_scope


def list_employees(context, params):
    actor = context.membership
    if not has_capability_any_scope(actor, "employees.view"):
        raise PermissionDenied(t("admin.not_allowed"))
    page = paginate(employees_for(context.organization_id, params), params)
    availability = employee_availability(context.organization_id, page.items)
    payload = page_payload(page, lambda employee: employee_payload(employee, actor,
        availability=availability[employee.user_id]))
    payload["invitations"] = pending_invitations_payload(context.organization, params)
    return payload


def employee_detail(context, user_id):
    actor = context.membership
    profile = profile_for(context, user_id)
    if profile is None or not has_capability_any_scope(actor, "employees.view"):
        raise NotFound(t("admin.employee_not_found"))
    return {"employee": employee_payload(profile, actor, include_detail=True)}


def employee_avatar(context, user_id):
    membership = OrganizationMembership.objects.select_related("user").filter(
        organization_id=context.organization_id, user_id=user_id).first()
    if membership is None or not membership.user.avatar:
        raise NotFound(t("admin.photo_not_found"))
    return membership.user.avatar, membership.user.avatar_content_type or "application/octet-stream"
