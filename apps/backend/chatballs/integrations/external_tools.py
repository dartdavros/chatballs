"""Снимок инструментов MCP-сервера и вызов инструмента (SPEC-0023 R-2).

Список инструментов сервер отдаёт по ``tools/list``; здесь он приводится к
снимку и хранится в интеграции. Снимок меняется только по «Обновить список
инструментов»: при ошибке прежний список остаётся, а интерфейс показывает его
приглушённым вместе с причиной.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils import timezone

from chatballs.i18n import t
from chatballs.integrations import mcp_client
from chatballs.integrations.external_check import (
    ERROR_STATES,
    check_timeout,
    error_state,
    error_text,
)
from chatballs.integrations.external_headers import request_headers
from chatballs.integrations.models import Integration, IntegrationProvider, IntegrationStatus
from chatballs.tenancy.context import TenantContext

MAX_NAME_LENGTH = 128
_EMPTY_SCHEMA = {"type": "object", "properties": {}}


def tools_snapshot(raw_tools: list[dict]) -> list[dict]:
    """Привести ответ ``tools/list`` к снимку; инструмент без имени пропускается."""
    snapshot: list[dict] = []
    seen: set[str] = set()
    for raw in raw_tools:
        name = raw.get("name")
        if not isinstance(name, str) or not name or len(name) > MAX_NAME_LENGTH or name in seen:
            continue
        seen.add(name)
        annotations = raw.get("annotations")
        annotations = annotations if isinstance(annotations, dict) else {}
        schema = raw.get("inputSchema")
        snapshot.append(
            {
                "name": name,
                "title": _text(raw.get("title")) or _text(annotations.get("title")),
                "description": _text(raw.get("description")),
                "input_schema": schema if isinstance(schema, dict) else dict(_EMPTY_SCHEMA),
                # Отметку ставит только явное true: её отсутствие — «может изменять».
                "read_only_hint": annotations.get("readOnlyHint") is True,
                **({"annotations": {"destructiveHint": True}} if annotations.get("destructiveHint") is True else {}),
            }
        )
    return snapshot


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def refresh_tools(*, context: TenantContext, integration: Integration) -> Integration:
    """Запросить список инструментов и сохранить снимок со временем обновления."""
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    if integration.provider != IntegrationProvider.MCP:
        raise ValidationError({"integration": t("integrations.check_unsupported")})
    url = str(integration.config.get("url", ""))
    update_fields = ["status", "last_error", "last_error_code", "last_checked_at", "updated_at"]
    try:
        raw_tools = mcp_client.list_tools(
            url, headers=request_headers(integration), timeout=check_timeout()
        )
    except mcp_client.McpError as error:
        state = error_state(error.code)
        integration.status = IntegrationStatus.ERROR
        integration.last_error = error_text(state, url)
        integration.last_error_code = state
    else:
        integration.status = IntegrationStatus.OK
        integration.last_error = ""
        integration.last_error_code = ""
        integration.tools = tools_snapshot(raw_tools)
        integration.tools_refreshed_at = timezone.now()
        update_fields += ["tools", "tools_refreshed_at"]
    integration.last_checked_at = timezone.now()
    integration.save(update_fields=update_fields)
    if "tools" in update_fields:
        # Инструмент пропал из списка или потерял отметку сервера.
        from chatballs.ai.agent_tools import drop_unavailable_tools

        drop_unavailable_tools(integration)
    return integration


def call_tool(
    integration: Integration, name: str, arguments: dict, *, timeout: float
) -> mcp_client.McpToolResult:
    """Вызвать инструмент MCP-сервера; неудача — ``McpError`` с кодом."""
    return mcp_client.call_tool(
        str(integration.config.get("url", "")),
        name,
        arguments,
        headers=request_headers(integration),
        timeout=timeout,
    )


def tools_state(integration: Integration) -> str:
    """Состояние списка инструментов для интерфейса."""
    if integration.last_error_code in ERROR_STATES:
        return integration.last_error_code
    if integration.tools_refreshed_at is None:
        return "not_loaded"
    return "loaded" if integration.tools else "no_tools"


def tools_payload(integration: Integration) -> dict[str, object]:
    from chatballs.integrations.read_only import active_confirmations, confirmation_payload

    refreshed_at = integration.tools_refreshed_at
    confirmed = active_confirmations(integration)
    return {
        "tools": [
            {
                "name": tool["name"],
                "title": tool.get("title", ""),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("input_schema", {}),
                "readOnlyHint": bool(tool.get("read_only_hint")),
                # Подтверждение администратора для инструмента без отметки сервера.
                "readOnlyConfirmation": confirmation_payload(confirmed.get(tool["name"])),
            }
            for tool in integration.tools
        ],
        "toolsRefreshedAt": refreshed_at.isoformat() if refreshed_at else None,
        "toolsState": tools_state(integration),
    }
