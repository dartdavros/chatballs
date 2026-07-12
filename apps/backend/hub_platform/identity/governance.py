"""Target-aware governance policy для управления сотрудниками (ADR-HUB-0027 этап 2).

Единая точка истины «кто может управлять каким сотрудником». Матрица SPEC-HUB-0016 §8:

- OWNER управляет ADMIN и EMPLOYEE; операции над самим OWNER — только ownership flow.
- ADMIN управляет только EMPLOYEE; не трогает OWNER и других ADMIN никаким действием.
- EMPLOYEE не управляет сотрудниками.

`change_role` и `transfer_ownership` доступны только OWNER. Защищённые действия ADMIN
не обходит через вспомогательные операции (block/reset/terminate/placement/access).
"""

from __future__ import annotations

from hub_platform.identity.models import EmployeeProfile, EmployeeRole


class EmployeeAction:
    VIEW = "view"
    CREATE = "create"
    UPDATE_PROFILE = "update_profile"
    CHANGE_ROLE = "change_role"
    CHANGE_PLACEMENT = "change_placement"
    CHANGE_ACCESS = "change_access"
    BLOCK = "block"
    UNBLOCK = "unblock"
    RESET_PASSWORD = "reset_password"
    TERMINATE_SESSIONS = "terminate_sessions"
    DELETE = "delete"
    TRANSFER_OWNERSHIP = "transfer_ownership"


# Действия, которые OWNER выполняет над обычными и привилегированными целями, а ADMIN —
# только над EMPLOYEE. change_role/transfer_ownership обрабатываются отдельно (owner-only).
_TARGET_ACTIONS = frozenset(
    {
        EmployeeAction.VIEW,
        EmployeeAction.UPDATE_PROFILE,
        EmployeeAction.CHANGE_PLACEMENT,
        EmployeeAction.CHANGE_ACCESS,
        EmployeeAction.BLOCK,
        EmployeeAction.UNBLOCK,
        EmployeeAction.RESET_PASSWORD,
        EmployeeAction.TERMINATE_SESSIONS,
        EmployeeAction.DELETE,
    }
)


def _is_active_manager(actor: EmployeeProfile | None) -> bool:
    return (
        actor is not None
        and not actor.is_blocked
        and actor.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
    )


def can_create_role(actor: EmployeeProfile | None, new_role: str) -> bool:
    """Кого actor вправе создать. OWNER — ADMIN или EMPLOYEE; ADMIN — только EMPLOYEE.

    Второй OWNER через обычный create не создаётся (инвариант ровно одного владельца)."""
    if not _is_active_manager(actor):
        return False
    if new_role == EmployeeRole.OWNER:
        return False
    if new_role == EmployeeRole.ADMIN:
        return actor.role == EmployeeRole.OWNER
    if new_role == EmployeeRole.EMPLOYEE:
        return True
    return False


def can_manage_employee(
    actor: EmployeeProfile | None,
    target: EmployeeProfile | None,
    action: str,
) -> bool:
    """Может ли actor выполнить action над target (SPEC-HUB-0016 §8).

    Порядок проверки повторяет ADR-HUB-0027: активный менеджер → одна организация →
    роль target → owner-only для смены роли и передачи владения."""
    if not _is_active_manager(actor):
        return False

    if action == EmployeeAction.TRANSFER_OWNERSHIP:
        # Передаёт владение только действующий OWNER; target обязателен и той же организации.
        return (
            actor.role == EmployeeRole.OWNER
            and target is not None
            and target.organization_id == actor.organization_id
            and target.role != EmployeeRole.OWNER
        )

    if target is None or target.organization_id != actor.organization_id:
        return False

    # Владельца не трогает обычными действиями никто — только ownership flow выше.
    if target.role == EmployeeRole.OWNER:
        return False

    # Смена роли (в т.ч. назначение ADMIN) — исключительно OWNER.
    if action == EmployeeAction.CHANGE_ROLE:
        return actor.role == EmployeeRole.OWNER

    if action not in _TARGET_ACTIONS:
        return False

    # Другого ADMIN изменяет только OWNER; EMPLOYEE — любой активный менеджер.
    if target.role == EmployeeRole.ADMIN:
        return actor.role == EmployeeRole.OWNER
    return True


def employee_management_flags(
    actor: EmployeeProfile | None,
    target: EmployeeProfile,
) -> dict[str, bool]:
    """Флаги доступных действий над target для actor — backend как источник истины
    для скрытия недоступных действий во фронтенде (ADR-HUB-0027)."""
    return {
        "canView": can_manage_employee(actor, target, EmployeeAction.VIEW),
        "canUpdateProfile": can_manage_employee(actor, target, EmployeeAction.UPDATE_PROFILE),
        "canChangeRole": can_manage_employee(actor, target, EmployeeAction.CHANGE_ROLE),
        "canChangePlacement": can_manage_employee(actor, target, EmployeeAction.CHANGE_PLACEMENT),
        "canBlock": can_manage_employee(actor, target, EmployeeAction.BLOCK),
        "canUnblock": can_manage_employee(actor, target, EmployeeAction.UNBLOCK),
        "canResetPassword": can_manage_employee(actor, target, EmployeeAction.RESET_PASSWORD),
        "canTerminateSessions": can_manage_employee(actor, target, EmployeeAction.TERMINATE_SESSIONS),
        "canTransferOwnership": can_manage_employee(actor, target, EmployeeAction.TRANSFER_OWNERSHIP),
    }
