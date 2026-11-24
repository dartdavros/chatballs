"""Проверка соединения с внешним сервером и её ошибки (SPEC-0023 R-5).

MCP-сервер проверяется вызовом ``initialize``; HTTP-запрос не вызывается —
проверяется только, что его адрес разрешён. Ошибка — код состояния и фраза
«что случилось и где чинить» из словаря; ответа чужого сервера в ней нет.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from django.conf import settings

from chatballs.i18n import t
from chatballs.integrations import mcp_client
from chatballs.integrations.external_headers import request_headers
from chatballs.integrations.external_server import template_probe_url
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.integrations.tool_network import ToolAddressRejected, check_tool_url

# Состояния ошибки сервера, которые различает интерфейс.
UNREACHABLE = mcp_client.UNREACHABLE
UNAUTHORIZED = mcp_client.UNAUTHORIZED
ADDRESS_FORBIDDEN = mcp_client.ADDRESS_FORBIDDEN
ERROR_STATES = (UNREACHABLE, UNAUTHORIZED, ADDRESS_FORBIDDEN)


def check_timeout() -> float:
    return settings.CHATBALLS_AI_REQUEST_TIMEOUT


def error_state(code: str) -> str:
    """Свести причину к состоянию: всё, что не про доступ, — «недоступен»."""
    return code if code in (UNAUTHORIZED, ADDRESS_FORBIDDEN) else UNREACHABLE


def error_text(state: str, url: str) -> str:
    try:
        host = urlsplit(url).hostname or url
    except ValueError:
        host = url
    return t(f"integrations.server_{state}", host=host)


def _address_state(error: ToolAddressRejected) -> str:
    return UNREACHABLE if error.code == "unresolved" else ADDRESS_FORBIDDEN


def check_external_server(integration: Integration) -> tuple[bool, str, str]:
    """Вернуть (успех, фраза об ошибке, код состояния)."""
    from chatballs.identity.demo_seed.north_wind.local_transport import local_demo_target

    url = str(integration.config.get("url", ""))
    headers = request_headers(integration)
    state = ""
    if integration.provider == IntegrationProvider.MCP:
        try:
            mcp_client.ping(url, headers=headers, timeout=check_timeout())
        except mcp_client.McpError as error:
            state = error_state(error.code)
    else:
        try:
            target_url = template_probe_url(url)
            if local_demo_target(target_url, headers) is None:
                check_tool_url(target_url)
        except ToolAddressRejected as error:
            state = _address_state(error)
        except ValueError:
            state = UNREACHABLE
    if state:
        return False, error_text(state, url), state
    return True, "", ""
