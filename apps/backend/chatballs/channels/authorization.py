"""Авторизация операций над каналами (SPEC-CHATBALLS-0031 §3).

После упразднения отделов и scope-модели проверки сведены к роли: OWNER и
ADMIN управляют каналами, EMPLOYEE их не видит и не меняет. Названия helpers
сохранены, чтобы не менять все call sites одновременно.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from chatballs.i18n import t
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
    """``operation`` — ключ каталога, а не готовый текст: отказ читает человек."""

    if not has_organization_capability(context, CHANNELS_MANAGE):
        raise PermissionDenied(t("channels.operation_needs_manage", operation=t(operation)))


def require_channel_manage(context: TenantContext) -> None:
    if not has_organization_capability(context, CHANNELS_MANAGE):
        raise PermissionDenied(t("channels.no_rights_to_change"))


def require_connections_manage(context: TenantContext) -> None:
    if not has_organization_capability(context, INTEGRATIONS_MANAGE):
        raise PermissionDenied(t("channels.binding_needs_manage"))
