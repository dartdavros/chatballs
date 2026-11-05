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
# это проверяют employee-сервисы). EMPLOYEE и базовые права SUPERVISOR ограничены
# чатом; отдельная область контроля SUPERVISOR хранится по ADR-0033.
# Deny-by-default сохраняется; произвольных профилей доступа и отделов нет.


# Руководство организации: видит всё независимо от групп. Набор один и тот же
# в проверке доступа, в видимости диалогов и в подборе получателей уведомлений,
# поэтому записан здесь один раз.
MANAGEMENT_ROLES = frozenset({EmployeeRole.OWNER, EmployeeRole.ADMIN})


@dataclass(frozen=True, slots=True)
class ResourceScope:
    organization_id: int


def _active_membership(actor) -> OrganizationMembership | None:
    """Validate an already-resolved membership; never infer its organization."""
    if not isinstance(actor, OrganizationMembership):
        return None
    return OrganizationMembership.objects.select_related("user").filter(
        pk=actor.pk, organization_id=actor.organization_id,
        blocked_at__isnull=True, user__is_active=True,
    ).first()


def _role_capabilities(role: str) -> frozenset[str]:
    if role == EmployeeRole.OWNER:
        return ALL_CAPABILITIES
    if role == EmployeeRole.ADMIN:
        return ALL_CAPABILITIES - OWNER_ONLY_CAPABILITIES
    if role in {EmployeeRole.EMPLOYEE, EmployeeRole.SUPERVISOR}:
        return EMPLOYEE_CAPABILITIES
    return frozenset()


def authorize(actor, capability: str, resource_scope: ResourceScope) -> bool:
    """Deny-by-default решение по роли внутри проверенной организации."""
    profile = _active_membership(actor)
    if profile is None or profile.organization_id != resource_scope.organization_id:
        return False
    from chatballs.conversations.access import (
        ACTION_CAPABILITIES,
        authorize_conversation,
    )
    from chatballs.conversations.models import Conversation

    if isinstance(resource_scope, Conversation):
        current = Conversation.objects.filter(
            pk=resource_scope.pk, organization_id=profile.organization_id,
        ).first()
        return current is not None and authorize_conversation(profile, capability, current)
    if capability in ACTION_CAPABILITIES and profile.role not in MANAGEMENT_ROLES:
        return False
    return ACTION_CAPABILITIES.get(capability, capability) in _role_capabilities(profile.role)


def roles_with_capability(capability: str) -> frozenset[str]:
    """Роли, которым право выдано.

    Нужна там, где получателей ищут пачкой: спрашивать authorize() по одному
    сотруднику — это запрос в базу на каждого, то есть сотня запросов на сотню
    рабочих мест. Право выводится из роли, значит и отбирать можно по роли.
    """
    from chatballs.conversations.access import ACTION_CAPABILITIES

    capability = ACTION_CAPABILITIES.get(capability, capability)
    return frozenset(
        role for role in EmployeeRole.values if capability in _role_capabilities(role)
    )


def capabilities_in_any_scope(actor) -> frozenset[str]:
    """Current role capabilities, resolved once for a catalog request."""
    profile = _active_membership(actor)
    if profile is None:
        return frozenset()
    from chatballs.conversations.access import ACTION_CAPABILITIES

    capabilities = _role_capabilities(profile.role)
    return capabilities | frozenset(alias for alias, base in ACTION_CAPABILITIES.items() if base in capabilities)


def has_capability_any_scope(actor, capability: str) -> bool:
    return capability in capabilities_in_any_scope(actor)


def can_administer_access(actor) -> bool:
    profile = _active_membership(actor)
    return profile is not None and profile.role in MANAGEMENT_ROLES


def conversation_visibility(actor) -> dict | None:
    """Видимость диалогов (ADR-CHATBALLS-0043 §4).

    None — без ограничений (OWNER/ADMIN). Иначе словарь для построения фильтра:
    рабочие группы, назначения, участие и отдельно подконтрольные группы.
    Пустой доступ (нет membership) — {"none": True}.
    """
    profile = _active_membership(actor)
    if profile is None:
        return {"none": True}
    if profile.role not in EmployeeRole.values:
        return {"none": True}
    if profile.role in MANAGEMENT_ROLES:
        return None
    from chatballs.identity.group_models import member_group_ids

    return {
        "group_ids": member_group_ids(profile),
        "user_id": profile.user_id,
        "membership_id": profile.pk,
        "supervised_group_ids": set(profile.supervision_links.values_list("group_id", flat=True))
        if profile.role == EmployeeRole.SUPERVISOR else set(),
    }


def get_effective_access(actor) -> dict[str, object]:
    profile = _active_membership(actor)
    if profile is None:
        return {"capabilities": [], "groups": [], "supervisedGroups": [], "reportCapabilities": []}
    from chatballs.identity.group_models import EmployeeGroupMember

    groups = [
        {"id": link.group_id, "name": link.group.name}
        for link in EmployeeGroupMember.objects.filter(employee=profile).select_related(
            "group"
        )
    ]
    groups.sort(key=lambda item: str(item["name"]))
    from chatballs.identity.supervision_models import supervised_groups_payload

    access = {
        "capabilities": sorted(_role_capabilities(profile.role)),
        "groups": groups,
        "supervisedGroups": (
            supervised_groups_payload(profile) if profile.role == EmployeeRole.SUPERVISOR else []
        ),
    }
    if profile.role == EmployeeRole.SUPERVISOR:
        from chatballs.conversations.access import SUPERVISION_CAPABILITIES

        access["supervisionCapabilities"] = sorted(SUPERVISION_CAPABILITIES) if access["supervisedGroups"] else []
    from chatballs.identity.report_access import report_actions

    access["reportCapabilities"] = report_actions(profile, access["supervisedGroups"])
    return access


def scope_for_resource(resource) -> ResourceScope | None:
    """Resolve canonical model relations; never trusts request parameters."""
    organization_id = getattr(resource, "organization_id", None)
    if organization_id is None:
        return None
    return ResourceScope(organization_id=organization_id)


def require_capability(actor, capability: str, resource) -> bool:
    scope = scope_for_resource(resource)
    from chatballs.conversations.models import Conversation

    return scope is not None and authorize(
        actor, capability, resource if isinstance(resource, Conversation) else scope
    )
