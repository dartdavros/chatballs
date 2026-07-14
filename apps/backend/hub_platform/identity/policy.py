from __future__ import annotations

from dataclasses import dataclass

from django.db.models import QuerySet

from hub_platform.identity.capabilities import (
    CAPABILITY_REGISTRY,
    PROTECTED_CAPABILITIES,
    ScopeType,
    capability_spec,
)
from hub_platform.identity.models import (
    EmployeeAccessAssignment,
    EmployeeRole,
    OrganizationMembership,
)


@dataclass(frozen=True, slots=True)
class ResourceScope:
    organization_id: int
    department_id: int | None = None


def _active_membership(actor) -> OrganizationMembership | None:
    """Resolve the authorization actor without guessing between organizations.

    C02 services can pass a membership directly. Legacy user-based routes remain
    available only while the user has exactly one membership and are removed in C03.
    """

    if isinstance(actor, OrganizationMembership):
        if not actor.user.is_active or actor.is_blocked:
            return None
        return actor
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False):
        return None
    try:
        membership = actor.memberships.get()
    except (
        OrganizationMembership.DoesNotExist,
        OrganizationMembership.MultipleObjectsReturned,
    ):
        return None
    return None if membership.is_blocked else membership


def _assignments(profile: OrganizationMembership) -> QuerySet[EmployeeAccessAssignment]:
    return (
        EmployeeAccessAssignment.objects.filter(
            employee=profile,
            revoked_at__isnull=True,
            access_profile__is_active=True,
        )
        .select_related("department", "access_profile")
        .prefetch_related("access_profile__capability_links")
    )


def authorize(actor, capability: str, resource_scope: ResourceScope) -> bool:
    """Deny-by-default capability and scope decision (SPEC-HUB-0017 §8)."""
    try:
        spec = capability_spec(capability)
    except ValueError:
        return False

    profile = _active_membership(actor)
    if profile is None or profile.organization_id != resource_scope.organization_id:
        return False
    if profile.role == EmployeeRole.OWNER:
        return True
    if profile.role == EmployeeRole.ADMIN:
        return capability not in PROTECTED_CAPABILITIES
    if profile.role != EmployeeRole.EMPLOYEE:
        return False

    for assignment in _assignments(profile):
        if assignment.scope_type not in spec.allowed_scopes:
            continue
        if assignment.scope_type == ScopeType.DEPARTMENT:
            if resource_scope.department_id is None:
                continue
            if assignment.department_id != resource_scope.department_id:
                continue
        codes = {
            link.capability_code for link in assignment.access_profile.capability_links.all()
        }
        if capability in codes:
            return True
    return False


def has_capability_any_scope(actor, capability: str) -> bool:
    profile = _active_membership(actor)
    if profile is None:
        return False
    if profile.role == EmployeeRole.OWNER:
        return capability in CAPABILITY_REGISTRY
    if profile.role == EmployeeRole.ADMIN:
        return capability in CAPABILITY_REGISTRY and capability not in PROTECTED_CAPABILITIES
    if profile.role != EmployeeRole.EMPLOYEE:
        return False
    return _assignments(profile).filter(
        access_profile__capability_links__capability_code=capability
    ).exists()


def can_administer_access(actor) -> bool:
    profile = _active_membership(actor)
    return profile is not None and profile.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}


def accessible_department_ids(actor, capability: str) -> set[int] | None:
    """None means all departments in the actor organization; set() means no access."""
    profile = _active_membership(actor)
    if profile is None:
        return set()
    if profile.role == EmployeeRole.OWNER:
        return None if capability in CAPABILITY_REGISTRY else set()
    if profile.role == EmployeeRole.ADMIN:
        return None if capability not in PROTECTED_CAPABILITIES else set()
    if profile.role != EmployeeRole.EMPLOYEE:
        return set()

    department_ids: set[int] = set()
    for assignment in _assignments(profile).filter(
        access_profile__capability_links__capability_code=capability
    ):
        if assignment.scope_type == ScopeType.ORGANIZATION:
            return None
        if assignment.department_id is not None:
            department_ids.add(assignment.department_id)
    return department_ids


def get_effective_access(actor) -> dict[str, object]:
    profile = _active_membership(actor)
    if profile is None:
        return {"capabilities": [], "accessScopes": []}

    if profile.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
        codes = sorted(
            code
            for code in CAPABILITY_REGISTRY
            if profile.role == EmployeeRole.OWNER or code not in PROTECTED_CAPABILITIES
        )
        return {
            "capabilities": codes,
            "accessScopes": [
                {
                    "scopeType": ScopeType.ORGANIZATION,
                    "departmentId": None,
                    "departmentCode": None,
                    "capabilities": codes,
                }
            ],
        }

    scope_codes: dict[tuple[str, int | None, str | None], set[str]] = {}
    for assignment in _assignments(profile):
        key = (
            assignment.scope_type,
            assignment.department_id,
            assignment.department.code if assignment.department_id else None,
        )
        codes = scope_codes.setdefault(key, set())
        for link in assignment.access_profile.capability_links.all():
            spec = CAPABILITY_REGISTRY.get(link.capability_code)
            if spec and spec.assignable and assignment.scope_type in spec.allowed_scopes:
                codes.add(link.capability_code)
    scopes = [
        {
            "scopeType": scope_type,
            "departmentId": department_id,
            "departmentCode": department_code,
            "capabilities": sorted(codes),
        }
        for (scope_type, department_id, department_code), codes in sorted(
            scope_codes.items(), key=lambda item: (item[0][0], item[0][1] or 0)
        )
        if codes
    ]
    return {
        "capabilities": sorted({code for scope in scopes for code in scope["capabilities"]}),
        "accessScopes": scopes,
    }


def scope_for_resource(resource) -> ResourceScope | None:
    """Resolve canonical model relations; never trusts request parameters."""
    organization_id = getattr(resource, "organization_id", None)
    if organization_id is None:
        return None
    department_id = getattr(resource, "department_id", None)
    if department_id is None:
        channel = getattr(resource, "channel", None)
        if channel is not None:
            department_id = channel.department_id
    if department_id is None:
        conversation = getattr(resource, "conversation", None)
        if conversation is not None:
            department_id = conversation.channel.department_id
    return ResourceScope(organization_id=organization_id, department_id=department_id)


def require_capability(actor, capability: str, resource) -> bool:
    scope = scope_for_resource(resource)
    return scope is not None and authorize(actor, capability, scope)
