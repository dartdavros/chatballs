from django.core.exceptions import ValidationError

from hub_platform.identity.capabilities import CAPABILITY_REGISTRY, ScopeType
from hub_platform.identity.models import (
    AccessProfile,
    Department,
    DepartmentStatus,
    EmployeeAccessAssignment,
    EmployeeProfile,
    EmployeeRole,
)


def allowed_profile_scopes(capability_codes: list[str]) -> set[str]:
    allowed = {ScopeType.ORGANIZATION, ScopeType.DEPARTMENT}
    for code in capability_codes:
        allowed.intersection_update(CAPABILITY_REGISTRY[code].allowed_scopes)
    return allowed


def create_access_assignment(
    *, actor: EmployeeProfile, employee: EmployeeProfile, payload: dict
) -> EmployeeAccessAssignment:
    if employee.role != EmployeeRole.EMPLOYEE:
        raise ValidationError("Access assignments are only allowed for EMPLOYEE")
    profile = AccessProfile.objects.filter(
        id=payload.get("profileId"),
        organization=actor.organization,
        is_active=True,
    ).first()
    if profile is None:
        raise ValidationError("Active access profile not found")

    scope_type = str(payload.get("scopeType", ""))
    department = None
    if scope_type == ScopeType.DEPARTMENT:
        department = Department.objects.filter(
            id=payload.get("departmentId"),
            organization=actor.organization,
            status=DepartmentStatus.ACTIVE,
        ).first()
        if department is None:
            raise ValidationError("Active department not found")
    elif scope_type != ScopeType.ORGANIZATION:
        raise ValidationError("Invalid scope type")

    capability_codes = list(
        profile.capability_links.values_list("capability_code", flat=True)
    )
    if scope_type not in allowed_profile_scopes(capability_codes):
        raise ValidationError("Access profile does not allow the requested scope")

    return EmployeeAccessAssignment.objects.create(
        employee=employee,
        access_profile=profile,
        scope_type=scope_type,
        department=department,
        assigned_by=actor,
    )
