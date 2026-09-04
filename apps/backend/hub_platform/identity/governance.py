"""Target-aware governance для управления сотрудниками (SPEC-HUB-0031 §3).

OWNER и ADMIN идентичны по правам: оба управляют любыми сотрудниками, включая
других администраторов. Отличия ровно два:

- владельца нельзя удалить и заблокировать (и нельзя сменить ему роль —
  единственный путь: передача владения);
- передача владения доступна только самому владельцу.
"""

from __future__ import annotations

from hub_platform.identity.models import EmployeeRole, OrganizationMembership


class EmployeeAction:
    VIEW = "view"
    CREATE = "create"
    UPDATE_PROFILE = "update_profile"
    CHANGE_ROLE = "change_role"
    CHANGE_GROUPS = "change_groups"
    BLOCK = "block"
    UNBLOCK = "unblock"
    RESET_PASSWORD = "reset_password"
    TERMINATE_SESSIONS = "terminate_sessions"
    DELETE = "delete"
    TRANSFER_OWNERSHIP = "transfer_ownership"


# Действия, запрещённые над владельцем для всех (SPEC-HUB-0031 §3);
# смена его роли возможна только через ownership flow.
_OWNER_PROTECTED_ACTIONS = frozenset(
    {
        EmployeeAction.CHANGE_ROLE,
        EmployeeAction.BLOCK,
        EmployeeAction.UNBLOCK,
        EmployeeAction.DELETE,
    }
)

_MANAGED_ACTIONS = frozenset(
    {
        EmployeeAction.VIEW,
        EmployeeAction.UPDATE_PROFILE,
        EmployeeAction.CHANGE_ROLE,
        EmployeeAction.CHANGE_GROUPS,
        EmployeeAction.BLOCK,
        EmployeeAction.UNBLOCK,
        EmployeeAction.RESET_PASSWORD,
        EmployeeAction.TERMINATE_SESSIONS,
        EmployeeAction.DELETE,
    }
)


def _is_active_manager(actor: OrganizationMembership | None) -> bool:
    return (
        actor is not None
        and not actor.is_blocked
        and actor.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
    )


def can_create_role(actor: OrganizationMembership | None, new_role: str) -> bool:
    """OWNER и ADMIN создают ADMIN или EMPLOYEE; второй OWNER не создаётся."""
    if not _is_active_manager(actor):
        return False
    return new_role in {EmployeeRole.ADMIN, EmployeeRole.EMPLOYEE}


def can_manage_employee(
    actor: OrganizationMembership | None,
    target: OrganizationMembership | None,
    action: str,
) -> bool:
    """Может ли actor выполнить action над target (SPEC-HUB-0031 §3)."""
    if not _is_active_manager(actor):
        return False

    if action == EmployeeAction.TRANSFER_OWNERSHIP:
        # Передаёт владение только действующий OWNER; target — не владелец.
        return (
            actor.role == EmployeeRole.OWNER
            and target is not None
            and target.organization_id == actor.organization_id
            and target.role != EmployeeRole.OWNER
        )

    if target is None or target.organization_id != actor.organization_id:
        return False
    if action not in _MANAGED_ACTIONS:
        return False
    if target.role == EmployeeRole.OWNER and action in _OWNER_PROTECTED_ACTIONS:
        return False
    return True


def employee_management_flags(
    actor: OrganizationMembership | None,
    target: OrganizationMembership,
) -> dict[str, bool]:
    """Флаги доступных действий над target — backend как источник истины
    для скрытия недоступных действий во фронтенде."""
    return {
        "canView": can_manage_employee(actor, target, EmployeeAction.VIEW),
        "canUpdateProfile": can_manage_employee(actor, target, EmployeeAction.UPDATE_PROFILE),
        "canChangeRole": can_manage_employee(actor, target, EmployeeAction.CHANGE_ROLE),
        "canChangeGroups": can_manage_employee(actor, target, EmployeeAction.CHANGE_GROUPS),
        "canBlock": can_manage_employee(actor, target, EmployeeAction.BLOCK),
        "canUnblock": can_manage_employee(actor, target, EmployeeAction.UNBLOCK),
        "canResetPassword": can_manage_employee(actor, target, EmployeeAction.RESET_PASSWORD),
        "canTerminateSessions": can_manage_employee(actor, target, EmployeeAction.TERMINATE_SESSIONS),
        "canTransferOwnership": can_manage_employee(actor, target, EmployeeAction.TRANSFER_OWNERSHIP),
    }
