"""Пофайловая авторизация канала (SPEC-HUB-0027 §5.2, ADR-HUB-0037 §9).

Часть операций требует organization scope, потому что затрагивает коммерческую
границу и маршрутизацию всей организации: создание, удаление, деактивация,
продукт и любой из пяти флагов политики. Department-scoped `channels.manage`
меняет только `name` и `department` в пределах доступных отделов.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from hub_platform.identity.policy import (
    ResourceScope,
    accessible_department_ids,
    authorize,
)
from hub_platform.tenancy.context import TenantContext

CHANNELS_VIEW = "channels.view"
CHANNELS_MANAGE = "channels.manage"
INTEGRATIONS_MANAGE = "integrations.manage"


def _membership(context: TenantContext):
    membership = context.membership
    if membership is None or membership.organization_id != context.organization_id:
        return None
    return membership


def department_ids_for(context: TenantContext, capability: str) -> set[int] | None:
    """None — все отделы организации, set() — доступа нет."""
    membership = _membership(context)
    if membership is None:
        return set()
    return accessible_department_ids(membership, capability)


def has_capability_in_scope(
    context: TenantContext, capability: str, *, department_id: int | None = None
) -> bool:
    membership = _membership(context)
    if membership is None:
        return False
    return authorize(
        membership,
        capability,
        ResourceScope(
            organization_id=context.organization_id, department_id=department_id
        ),
    )


def has_organization_capability(context: TenantContext, capability: str) -> bool:
    # ResourceScope без отдела покрывается только ORGANIZATION-назначением.
    return has_capability_in_scope(context, capability)


def require_organization_manage(context: TenantContext, *, operation: str) -> None:
    if not has_organization_capability(context, CHANNELS_MANAGE):
        raise PermissionDenied(
            f"{operation} требует organization-scoped channels.manage"
        )


def require_channel_manage(context: TenantContext, *, department_id: int | None) -> None:
    """Изменение в scope канала: department-scoped достаточно для своего отдела."""
    if not has_capability_in_scope(context, CHANNELS_MANAGE, department_id=department_id):
        raise PermissionDenied("Нет прав на изменение канала")


def require_department_change(
    context: TenantContext,
    *,
    current_department_id: int | None,
    target_department_id: int | None,
) -> None:
    """Смена отдела требует прав на обе стороны перехода.

    Если одна из сторон `null` — назначение отдела каналу без отдела или снятие
    отдела, — покрыть отсутствующую сторону department-назначением невозможно, а
    канал без отдела department-scoped сотруднику вообще не виден. Поэтому такой
    переход требует organization scope (SPEC §5.2).
    """
    if current_department_id is None or target_department_id is None:
        require_organization_manage(context, operation="Смена отдела канала")
        return
    for department_id in (current_department_id, target_department_id):
        require_channel_manage(context, department_id=department_id)


def require_connections_manage(context: TenantContext) -> None:
    if not has_organization_capability(context, INTEGRATIONS_MANAGE):
        raise PermissionDenied(
            "Привязка подключения требует organization-scoped integrations.manage"
        )
