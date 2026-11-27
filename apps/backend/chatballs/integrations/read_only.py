"""Инструменты внешнего сервера и отметка «только чтение» (SPEC-0023 R-3, R-6).

Агенту включается только инструмент, который читает. У MCP-инструмента это
отметка сервера ``readOnlyHint`` или подтверждение администратора; HTTP-запрос
читает, если он ``GET`` или ``POST`` с отметкой «Только чтение».
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chatballs.i18n import t
from chatballs.identity.models import HumanUser
from chatballs.integrations.http_methods import READ_METHODS
from chatballs.integrations.models import (
    Integration,
    IntegrationProvider,
    ToolReadOnlyConfirmation,
)
from chatballs.tenancy.context import TenantContext


@dataclass(frozen=True)
class ServerTool:
    # Под каким именем инструмент включается агенту: у HTTP-запроса оно пустое.
    key: str
    name: str
    title: str
    description: str
    read_only: bool


def active_confirmations(integration: Integration) -> dict[str, ToolReadOnlyConfirmation]:
    """Действующие подтверждения сервера по имени инструмента."""
    confirmations = integration.tool_confirmations.filter(revoked_at__isnull=True)
    return {item.tool_name: item for item in confirmations.select_related("confirmed_by")}


def server_tools(integration: Integration) -> list[ServerTool]:
    """Инструменты сервера с ответом, читает ли каждый."""
    config = integration.config
    if integration.provider == IntegrationProvider.HTTP:
        return [
            ServerTool(
                key="",
                name=str(config.get("tool_name", "")),
                title=integration.name,
                description=str(config.get("description", "")),
                read_only=(config.get("method", "GET") in READ_METHODS
                           or config.get("method") == "POST" and bool(config.get("read_only"))),
            )
        ]
    confirmed = active_confirmations(integration)
    return [
        ServerTool(
            key=tool["name"],
            name=tool["name"],
            title=tool.get("title") or tool["name"],
            description=tool.get("description", ""),
            read_only=bool(tool.get("read_only_hint")) or tool["name"] in confirmed,
        )
        for tool in integration.tools
    ]


def confirmation_payload(confirmation: ToolReadOnlyConfirmation | None) -> dict[str, object] | None:
    if confirmation is None:
        return None
    actor = confirmation.confirmed_by
    return {
        "confirmedBy": {"id": actor.id, "name": actor.full_name or actor.email} if actor else None,
        "confirmedAt": confirmation.confirmed_at.isoformat(),
    }


def _unconfirmed_tool(*, context: TenantContext, integration: Integration, name: object) -> str:
    """Имя инструмента из снимка, которому подтверждение имеет смысл."""
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    tool = next(
        (
            tool
            for tool in integration.tools
            if integration.provider == IntegrationProvider.MCP and tool["name"] == name
        ),
        None,
    )
    if tool is None:
        raise ValidationError({"name": t("integrations.tool_not_in_list")})
    if tool.get("read_only_hint"):
        raise ValidationError({"name": t("integrations.tool_read_only_by_server")})
    return tool["name"]


@transaction.atomic
def confirm_read_only(
    *, context: TenantContext, integration: Integration, name: object, confirmed: object, actor: HumanUser
) -> None:
    """Записать подтверждение; без отметки в окне оно не принимается."""
    tool_name = _unconfirmed_tool(context=context, integration=integration, name=name)
    if confirmed is not True:
        raise ValidationError({"confirmed": t("integrations.tool_confirmation_required")})
    ToolReadOnlyConfirmation.objects.update_or_create(
        integration=integration,
        tool_name=tool_name,
        defaults={
            "organization_id": integration.organization_id,
            "confirmed_by": actor,
            "confirmed_at": timezone.now(),
            "revoked_by": None,
            "revoked_at": None,
        },
    )


@transaction.atomic
def revoke_read_only(
    *, context: TenantContext, integration: Integration, name: object, actor: HumanUser
) -> None:
    """Снять подтверждение и выключить инструмент у всех агентов."""
    from chatballs.ai.agent_tools import drop_unavailable_tools

    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    updated = ToolReadOnlyConfirmation.objects.filter(
        integration=integration, tool_name=str(name), revoked_at__isnull=True
    ).update(revoked_by=actor, revoked_at=timezone.now())
    if not updated:
        raise ValidationError({"name": t("integrations.tool_not_confirmed")})
    drop_unavailable_tools(integration)
