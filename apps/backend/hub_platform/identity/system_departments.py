from __future__ import annotations

from hub_platform.identity.models import Department, Organization

# System department codes (ADR-HUB-0022, SPEC-HUB-0010 §4.1). These were
# previously hardcoded strings in bootstrap.py / conversations routing.
# Centralised here so provisioning and future callers share one source of truth.
SALES_CODE = "sales"
SUPPORT_CODE = "support"

_SYSTEM_DEPARTMENTS = (
    (SALES_CODE, "Продажи"),
    (SUPPORT_CODE, "Поддержка"),
)


def ensure_system_departments(organization: Organization) -> dict[str, Department]:
    """Create the sales and support departments for an organization if absent.
    Returns a {code: Department} mapping. Both departments are always created
    (SPEC-HUB-0021 §7): their use is governed by entitlement policy, not by the
    presence of the Department row."""
    result: dict[str, Department] = {}
    for code, name in _SYSTEM_DEPARTMENTS:
        department, _ = Department.objects.get_or_create(
            organization=organization,
            code=code,
            defaults={"name": name},
        )
        result[code] = department
    return result
