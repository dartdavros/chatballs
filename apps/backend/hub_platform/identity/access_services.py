from django.core.exceptions import ValidationError

from hub_platform.identity.capabilities import ScopeType
from hub_platform.identity.models import (
    AccessProfile,
    Department,
    DepartmentStatus,
    EmployeeAccessAssignment,
    EmployeeProfile,
)


def create_access_assignment(
    *, actor: EmployeeProfile, employee: EmployeeProfile, payload: dict
) -> EmployeeAccessAssignment:
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

    return EmployeeAccessAssignment.objects.create(
        employee=employee,
        access_profile=profile,
        scope_type=scope_type,
        department=department,
        assigned_by=actor,
    )

