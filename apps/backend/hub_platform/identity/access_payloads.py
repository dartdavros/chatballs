from hub_platform.identity.access_services import allowed_profile_scopes
from hub_platform.identity.capabilities import CAPABILITY_REGISTRY, capability_spec
from hub_platform.identity.models import AccessProfile, EmployeeAccessAssignment


def profile_payload(profile: AccessProfile) -> dict[str, object]:
    capability_codes = sorted(
        profile.capability_links.values_list("capability_code", flat=True)
    )
    assigned_count = getattr(profile, "active_assignment_count", None)
    if assigned_count is None:
        assigned_count = profile.assignments.filter(revoked_at__isnull=True).count()
    return {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "isSystem": profile.is_system,
        "isActive": profile.is_active,
        "capabilities": capability_codes,
        "allowedScopes": sorted(allowed_profile_scopes(capability_codes)),
        "assignedCount": assigned_count,
    }


def assignment_payload(assignment: EmployeeAccessAssignment) -> dict[str, object]:
    return {
        "id": assignment.id,
        "profile": profile_payload(assignment.access_profile),
        "scopeType": assignment.scope_type,
        "departmentId": assignment.department_id,
        "departmentCode": assignment.department.code if assignment.department_id else None,
        "revokedAt": assignment.revoked_at.isoformat() if assignment.revoked_at else None,
    }


def capability_codes(raw: object) -> tuple[list[str], str | None]:
    if not isinstance(raw, list) or any(not isinstance(code, str) for code in raw):
        return [], "capabilities must be a list of registry codes"
    codes = list(dict.fromkeys(raw))
    try:
        for code in codes:
            spec = capability_spec(code)
            if not spec.assignable or spec.protected:
                return [], f"Capability cannot be assigned: {code}"
    except ValueError as error:
        return [], str(error)
    return codes, None


def capability_registry_payload() -> list[dict[str, object]]:
    return [
        {
            "code": spec.code,
            "name": spec.name,
            "description": spec.description,
            "allowedScopes": sorted(spec.allowed_scopes),
            "assignable": spec.assignable,
            "protected": spec.protected,
        }
        for spec in CAPABILITY_REGISTRY.values()
    ]
