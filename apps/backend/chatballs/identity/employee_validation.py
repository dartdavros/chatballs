from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import (
    POSITION_TITLE_MAX_LENGTH,
    AuditResult,
    EmployeeGroup,
    EmployeeRole,
    OrganizationMembership,
)

ASSIGNABLE_ROLES = {EmployeeRole.ADMIN, EmployeeRole.EMPLOYEE}


def clean_position_title(raw: object) -> tuple[str, str | None]:
    value = str(raw or "").strip()
    if not value:
        return "", "Position title is required"
    if len(value) > POSITION_TITLE_MAX_LENGTH:
        return value, f"Position title must be at most {POSITION_TITLE_MAX_LENGTH} characters"
    return value, None


def resolve_groups(organization, raw: object) -> tuple[list[EmployeeGroup] | None, str | None]:
    """Валидирует список id групп из запроса; None на входе — «не менять»."""
    if raw is None:
        return None, None
    if not isinstance(raw, list) or any(not isinstance(item, int) for item in raw):
        return None, "groupIds must be a list of ids"
    requested = list(dict.fromkeys(raw))
    groups = list(EmployeeGroup.objects.filter(organization=organization, id__in=requested))
    if len(groups) != len(requested):
        return None, "Group not found"
    return groups, None


def deny_employee_action(
    request: Request, target: OrganizationMembership | None, action: str
) -> Response:
    actor_profile = request.tenant_context.membership
    record_audit_event(
        action="identity.employee_privileged_action_denied",
        actor=request.user,
        organization=actor_profile.organization,
        object_type="HumanUser",
        object_id=str(target.user_id) if target else "",
        result=AuditResult.DENIED,
        payload={"action": action, "targetRole": target.role if target else None},
        request=request,
    )
    return Response({"detail": "You cannot perform this action on this employee"}, status=403)
