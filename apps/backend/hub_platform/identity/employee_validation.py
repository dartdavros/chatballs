from rest_framework.request import Request
from rest_framework.response import Response

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import (
    POSITION_TITLE_MAX_LENGTH,
    AuditResult,
    Department,
    DepartmentStatus,
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


def resolve_department(organization, code: str) -> tuple[Department | None, str | None]:
    code = (code or "").strip()
    if not code:
        return None, None
    try:
        department = Department.objects.get(
            organization=organization, code=code, status=DepartmentStatus.ACTIVE
        )
    except Department.DoesNotExist:
        return None, "Department not found"
    return department, None


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
