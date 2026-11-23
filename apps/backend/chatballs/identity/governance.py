"""Target-aware governance для управления сотрудниками (SPEC-CHATBALLS-0031 §3).

OWNER и ADMIN идентичны по правам: оба управляют любыми сотрудниками, включая
других администраторов. Отличия ровно два:

- карточка владельца доступна только для просмотра;
- передача владения доступна только самому владельцу.
"""

from __future__ import annotations

from chatballs.identity.models import EmployeeRole, OrganizationMembership
from chatballs.identity.policy import can_administer_access


class EmployeeAction:
    VIEW = "view"
    CREATE = "create"
    UPDATE_PROFILE = "update_profile"
    CHANGE_ROLE = "change_role"
    CHANGE_GROUPS = "change_groups"
    CHANGE_SUPERVISED_GROUPS = "change_supervised_groups"
    BLOCK = "block"
    UNBLOCK = "unblock"
    RESET_PASSWORD = "reset_password"
    TERMINATE_SESSIONS = "terminate_sessions"
    DELETE = "delete"
    DISMISS = "dismiss"
    TRANSFER_OWNERSHIP = "transfer_ownership"


# Действия, запрещённые над владельцем для всех (SPEC-CHATBALLS-0031 §3);
# смена его роли возможна только через ownership flow.
_MANAGED_ACTIONS = frozenset(
    {
        EmployeeAction.VIEW,
        EmployeeAction.UPDATE_PROFILE,
        EmployeeAction.CHANGE_ROLE,
        EmployeeAction.CHANGE_GROUPS,
        EmployeeAction.CHANGE_SUPERVISED_GROUPS,
        EmployeeAction.BLOCK,
        EmployeeAction.UNBLOCK,
        EmployeeAction.RESET_PASSWORD,
        EmployeeAction.TERMINATE_SESSIONS,
        EmployeeAction.DELETE,
        EmployeeAction.DISMISS,
    }
)


def _is_active_manager(actor: OrganizationMembership | None) -> bool:
    return can_administer_access(actor)


def can_create_role(actor: OrganizationMembership | None, new_role: str) -> bool:
    """OWNER и ADMIN назначают фиксированные роли; второй OWNER не создаётся."""
    if not _is_active_manager(actor):
        return False
    return new_role in {EmployeeRole.ADMIN, EmployeeRole.SUPERVISOR, EmployeeRole.EMPLOYEE}


def can_manage_employee(
    actor: OrganizationMembership | None,
    target: OrganizationMembership | None,
    action: str,
) -> bool:
    """Может ли actor выполнить action над target (SPEC-CHATBALLS-0031 §3)."""
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
    if target.role == EmployeeRole.OWNER:
        return action == EmployeeAction.VIEW
    if target.dismissed_at is not None:
        return action in {EmployeeAction.VIEW, EmployeeAction.DISMISS}
    return True


def employee_management_flags(
    actor: OrganizationMembership | None,
    target: OrganizationMembership,
) -> dict[str, bool]:
    """Флаги доступных действий над target — backend как источник истины
    для скрытия недоступных действий во фронтенде."""
    return {
        "canView": can_manage_employee(actor, target, EmployeeAction.VIEW),
        "canDismiss": target.dismissed_at is None and can_manage_employee(actor, target, EmployeeAction.DISMISS),
        "canUpdateProfile": can_manage_employee(actor, target, EmployeeAction.UPDATE_PROFILE),
        "canChangeRole": can_manage_employee(actor, target, EmployeeAction.CHANGE_ROLE),
        "canChangeGroups": can_manage_employee(actor, target, EmployeeAction.CHANGE_GROUPS),
        "canChangeSupervisedGroups": can_manage_employee(
            actor, target, EmployeeAction.CHANGE_SUPERVISED_GROUPS
        ),
        "canBlock": can_manage_employee(actor, target, EmployeeAction.BLOCK),
        "canUnblock": can_manage_employee(actor, target, EmployeeAction.UNBLOCK),
        "canResetPassword": can_manage_employee(actor, target, EmployeeAction.RESET_PASSWORD),
        "canTerminateSessions": can_manage_employee(actor, target, EmployeeAction.TERMINATE_SESSIONS),
        "canTransferOwnership": (
            _is_active_manager(actor) and actor.role == EmployeeRole.OWNER
            and actor.pk == target.pk and target.role == EmployeeRole.OWNER
        ),
    }
