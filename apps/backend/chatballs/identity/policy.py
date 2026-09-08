from __future__ import annotations

from dataclasses import dataclass

from chatballs.identity.capabilities import (
    ALL_CAPABILITIES,
    EMPLOYEE_CAPABILITIES,
    OWNER_ONLY_CAPABILITIES,
)
from chatballs.identity.models import EmployeeRole, OrganizationMembership

# Ролевая авторизация (SPEC-CHATBALLS-0031 §3, ADR-CHATBALLS-0043): OWNER и ADMIN идентичны
# (кроме ownership.transfer и невозможности удалить/заблокировать владельца —
# это проверяют employee-сервисы), EMPLOYEE ограничен чатом. Deny-by-default
# сохраняется; scope-модель и отделы упразднены.


@dataclass(frozen=True, slots=True)
class ResourceScope:
    organization_id: int


def _active_membership(actor) -> OrganizationMembership | None:
    """Validate an already-resolved membership; never infer its organization."""
    if not isinstance(actor, OrganizationMembership):
        return None
    if not actor.user.is_active or actor.is_blocked:
        return None
    return actor


def _role_capabilities(role: str) -> frozenset[str]:
    if role == EmployeeRole.OWNER:
        return ALL_CAPABILITIES
    if role == EmployeeRole.ADMIN:
        return ALL_CAPABILITIES - OWNER_ONLY_CAPABILITIES
    if role == EmployeeRole.EMPLOYEE:
        return EMPLOYEE_CAPABILITIES
    return frozenset()


def authorize(actor, capability: str, resource_scope: ResourceScope) -> bool:
    """Deny-by-default решение по роли внутри проверенной организации."""
    profile = _active_membership(actor)
    if profile is None or profile.organization_id != resource_scope.organization_id:
        return False
    return capability in _role_capabilities(profile.role)


def has_capability_any_scope(actor, capability: str) -> bool:
    profile = _active_membership(actor)
    if profile is None:
        return False
    return capability in _role_capabilities(profile.role)


def can_administer_access(actor) -> bool:
    profile = _active_membership(actor)
    return profile is not None and profile.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}


def conversation_visibility(actor) -> dict | None:
    """Видимость диалогов (ADR-CHATBALLS-0043 §4).

    None — без ограничений (OWNER/ADMIN). Иначе словарь для построения фильтра:
    диалоги групп сотрудника + диалоги без группы + назначенные ему.
    Пустой доступ (нет membership) — {"none": True}.
    """
    profile = _active_membership(actor)
    if profile is None:
        return {"none": True}
    if profile.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
        return None
    from chatballs.identity.group_models import member_group_ids

    return {
        "group_ids": member_group_ids(profile),
        "user_id": profile.user_id,
    }


def get_effective_access(actor) -> dict[str, object]:
    profile = _active_membership(actor)
    if profile is None:
        return {"capabilities": [], "groups": []}
    from chatballs.identity.group_models import EmployeeGroupMember

    groups = [
        {"id": link.group_id, "name": link.group.name}
        for link in EmployeeGroupMember.objects.filter(employee=profile).select_related(
            "group"
        )
    ]
    groups.sort(key=lambda item: str(item["name"]))
    return {
        "capabilities": sorted(_role_capabilities(profile.role)),
        "groups": groups,
    }


def scope_for_resource(resource) -> ResourceScope | None:
    """Resolve canonical model relations; never trusts request parameters."""
    organization_id = getattr(resource, "organization_id", None)
    if organization_id is None:
        return None
    return ResourceScope(organization_id=organization_id)


def require_capability(actor, capability: str, resource) -> bool:
    scope = scope_for_resource(resource)
    return scope is not None and authorize(actor, capability, scope)
