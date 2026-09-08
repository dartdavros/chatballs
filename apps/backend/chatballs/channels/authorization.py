"""Авторизация операций над каналами (SPEC-CHATBALLS-0031 §3).

После упразднения отделов и scope-модели проверки сведены к роли: OWNER и
ADMIN управляют каналами, EMPLOYEE их не видит и не меняет. Названия helpers
сохранены, чтобы не менять все call sites одновременно.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from chatballs.identity.policy import has_capability_any_scope
from chatballs.tenancy.context import TenantContext

CHANNELS_VIEW = "channels.view"
CHANNELS_MANAGE = "channels.manage"
INTEGRATIONS_MANAGE = "integrations.manage"


def _membership(context: TenantContext):
    membership = context.membership
    if membership is None or membership.organization_id != context.organization_id:
        return None
    return membership


def has_organization_capability(context: TenantContext, capability: str) -> bool:
    membership = _membership(context)
    if membership is None:
        return False
    return has_capability_any_scope(membership, capability)


def require_organization_manage(context: TenantContext, *, operation: str) -> None:
    if not has_organization_capability(context, CHANNELS_MANAGE):
        raise PermissionDenied(f"{operation} требует channels.manage")


def require_channel_manage(context: TenantContext) -> None:
    if not has_organization_capability(context, CHANNELS_MANAGE):
        raise PermissionDenied("Нет прав на изменение канала")


def require_connections_manage(context: TenantContext) -> None:
    if not has_organization_capability(context, INTEGRATIONS_MANAGE):
        raise PermissionDenied("Привязка подключения требует integrations.manage")
