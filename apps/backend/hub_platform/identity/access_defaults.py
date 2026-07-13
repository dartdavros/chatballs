from __future__ import annotations

from hub_platform.identity.capabilities import ScopeType
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    Department,
    EmployeeAccessAssignment,
    EmployeeProfile,
)


SYSTEM_PROFILE_CAPABILITIES = {
    "Sales operator": (
        "conversations.view",
        "conversations.operate",
        "conversations.call",
        "customers.view",
        "customers.manage",
        "products.view",
        "sales.view",
        "sales.operate",
    ),
    "Support operator": (
        "conversations.view",
        "conversations.operate",
        "conversations.call",
        "customers.view",
        "products.view",
        "support.view",
        "support.operate",
    ),
}


def ensure_system_assignment(
    *,
    employee: EmployeeProfile,
    assigned_by: EmployeeProfile,
    department: Department,
    profile_name: str,
) -> EmployeeAccessAssignment:
    capabilities = SYSTEM_PROFILE_CAPABILITIES[profile_name]
    profile, _ = AccessProfile.objects.get_or_create(
        organization=employee.organization,
        name=profile_name,
        defaults={
            "description": "System access profile",
            "is_system": True,
            "is_active": True,
        },
    )
    for code in capabilities:
        AccessProfileCapability.objects.get_or_create(
            access_profile=profile, capability_code=code
        )
    assignment = EmployeeAccessAssignment.objects.filter(
        employee=employee,
        access_profile=profile,
        scope_type=ScopeType.DEPARTMENT,
        department=department,
        revoked_at__isnull=True,
    ).first()
    if assignment is not None:
        return assignment
    return EmployeeAccessAssignment.objects.create(
        employee=employee,
        access_profile=profile,
        scope_type=ScopeType.DEPARTMENT,
        department=department,
        assigned_by=assigned_by,
    )

