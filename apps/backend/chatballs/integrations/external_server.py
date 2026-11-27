"""Интеграция «Внешний сервер»: MCP-сервер или HTTP-запрос (SPEC-0023 R-1–R-4).

Настройки приходят в ``externalServer`` и хранятся в ``config`` в snake_case:
описание, адрес, заголовки; у HTTP-запроса — ещё имя инструмента, метод,
отметка «только чтение» и параметры. Секретные значения заголовков лежат
отдельно, в зашифрованном ``secret_headers``.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.integrations.external_errors import SettingsErrors
from chatballs.integrations.external_headers import (
    dump_secret_headers,
    headers_payload,
    normalize_headers,
    stored_secret_headers,
)
from chatballs.integrations.external_parameters import (
    normalize_parameters,
    parameters_payload,
    submitted_names,
)
from chatballs.integrations.http_methods import METHODS
from chatballs.integrations.models import (
    PROVIDER_KIND,
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from chatballs.integrations.tool_network import ToolAddressRejected, check_tool_url

TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")


def is_external_server(provider: str) -> bool:
    return PROVIDER_KIND.get(provider) == IntegrationKind.EXTERNAL_SERVER


def _check_address(url: str, *, errors: SettingsErrors, allow_private: bool | None = None) -> None:
    try:
        check_tool_url(url, allow_private=allow_private)
    except ToolAddressRejected as error:
        errors.add_text("url", str(error))
    except ValueError:
        # Адрес, который не разобрать: «http://[::1».
        errors.add("url", "integrations.tool_address_unresolved")


def _check_template_address(url: str, *, errors: SettingsErrors) -> None:
    """Проверить сервер из шаблона адреса.

    Подстановки допустимы только после имени сервера: иначе хост выбирала бы
    модель, и заголовки авторизации ушли бы на него. Значения подстановок
    появятся только в ходе, итоговый адрес клиент проверит ещё раз.
    """
    try:
        host_has_placeholder = "{" in urlsplit(url).netloc
    except ValueError:
        host_has_placeholder = True
    if host_has_placeholder:
        errors.add("url", "integrations.tool_address_unresolved")
    else:
        _check_address(template_probe_url(url), errors=errors)


def template_probe_url(url: str) -> str:
    """Адрес из шаблона с условными значениями — чтобы проверить сам сервер."""
    return _PLACEHOLDER.sub("x", url)


def validate_http_address(url: str) -> None:
    """Проверка адреса редактора без сохранения и HTTP-вызова инструмента."""
    errors = SettingsErrors()
    _check_template_address(url, errors=errors)
    errors.raise_if_any()


def _mcp_config(raw: dict, *, errors: SettingsErrors) -> dict:
    from chatballs.identity.instance_settings import tools_private_network_allowed

    url = str(raw.get("url") or "").strip()
    if not url:
        errors.add("url", "integrations.tool_url_required")
    else:
        # http — только там, где установка разрешила адреса локальной сети (R-2).
        allow_private = tools_private_network_allowed()
        if url.lower().startswith("http://") and not allow_private:
            errors.add("url", "settings.url_scheme_required", schemes="https://")
        else:
            _check_address(url, errors=errors, allow_private=allow_private)
    return {"description": str(raw.get("description") or "").strip(), "url": url}


def _http_config(raw: dict, *, integration: Integration, errors: SettingsErrors) -> dict:
    tool_name = str(raw.get("toolName") or "").strip()
    if not TOOL_NAME_PATTERN.match(tool_name):
        errors.add("toolName", "integrations.tool_name_invalid")
    description = str(raw.get("description") or "").strip()
    if not description:
        errors.add("description", "integrations.tool_description_required")
    method = str(raw.get("method") or "GET").upper()
    if method not in METHODS:
        errors.add("method", "integrations.tool_method_invalid")
    url = str(raw.get("url") or "").strip()
    placeholders = set(_PLACEHOLDER.findall(url))
    parameters = normalize_parameters(
        raw.get("parameters", []),
        method=method,
        placeholders=placeholders,
        organization=integration.organization,
        errors=errors,
    )
    if not url:
        errors.add("url", "integrations.tool_url_required")
    else:
        for name in sorted(placeholders - submitted_names(raw.get("parameters"))):
            errors.add("url", "integrations.tool_url_placeholder_unknown", name=name)
        _check_template_address(url, errors=errors)
    return {
        "description": description,
        "url": url,
        "tool_name": tool_name,
        "method": method,
        # У GET отметки нет: он читает по определению.
        "read_only": method == "POST" and bool(raw.get("readOnly")),
        "parameters": parameters,
    }


def apply_external_settings(integration: Integration, raw: object) -> None:
    """Проверить настройки из запроса и записать их в интеграцию (без save)."""
    if not isinstance(raw, dict):
        raise ValidationError({"externalServer": t("api.object_required")})
    errors = SettingsErrors()
    if integration.provider == IntegrationProvider.MCP:
        config = _mcp_config(raw, errors=errors)
    else:
        config = _http_config(raw, integration=integration, errors=errors)
    headers, secrets = normalize_headers(
        raw.get("headers", []),
        previous_secrets=stored_secret_headers(integration),
        errors=errors,
    )
    errors.raise_if_any()
    integration.config = {**config, "headers": headers}
    integration.secret_headers = dump_secret_headers(secrets)


def external_server_payload(integration: Integration) -> dict[str, object]:
    config = integration.config
    payload: dict[str, object] = {
        "type": integration.provider.lower(),
        "description": config.get("description", ""),
        "url": config.get("url", ""),
        "headers": headers_payload(config.get("headers")),
    }
    if integration.provider == IntegrationProvider.HTTP:
        payload.update(
            toolName=config.get("tool_name", ""),
            method=config.get("method", "GET"),
            readOnly=bool(config.get("read_only")),
            parameters=parameters_payload(config.get("parameters")),
        )
    return payload
