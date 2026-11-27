"""HTTP-инструмент: запрос из шаблона, аргументов модели и данных клиента.

Параметр уходит в адрес (с URL-кодированием), в query или в тело JSON
(SPEC-0023 R-3). Значение параметра с источником «ai» присылает модель,
привязанного — подставляет сервер из данных клиента: имени, e-mail, телефона
контакта или своего поля веб-подключения (R-4). Привязанного параметра в схеме
для модели нет, а если обязательное привязанное значение взять неоткуда,
инструмент в ходе не предлагается вовсе.

Значение из аргумента кодируется целиком и сервер в адресе не меняет; итоговый
адрес всё равно проверяет клиент (``tool_client.fetch``, R-16).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import quote, urlencode, urlsplit

from chatballs.i18n import t
from chatballs.integrations.external_headers import request_headers
from chatballs.integrations.external_parameters import CONTACT_FIELDS
from chatballs.integrations.external_server import template_probe_url
from chatballs.integrations.http_methods import BODY_METHODS, READ_METHODS
from chatballs.integrations.models import Integration
from chatballs.integrations.tool_client import ToolResponse, fetch
from chatballs.integrations.tool_network import ToolAddressRejected

MAX_VALUE_LENGTH = 2000
_NUMBER = re.compile(r"^-?\d{1,18}(\.\d{1,18})?$")
_MISSING = object()


@dataclass(frozen=True)
class ClientData:
    """Данные клиента, из которых сервер берёт привязанные параметры."""

    name: str = ""
    email: str = ""
    phone: str = ""
    # Свои поля: подключение → ключ → значение. В живом диалоге здесь только
    # веб-подключение самого диалога, вне веб-виджета — пусто.
    web_fields: Mapping[int, Mapping[str, object]] = field(default_factory=dict)


class ToolArgumentsRejected(Exception):
    """Аргументы модели не подходят параметрам; ``parameter`` — который из них."""

    code = "invalid_arguments"

    def __init__(self, parameter: str) -> None:
        super().__init__(parameter)
        self.parameter = parameter


@dataclass(frozen=True)
class HttpToolRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None


def _parameters(config: dict) -> list[dict]:
    stored = config.get("parameters")
    return stored if isinstance(stored, list) else []


def _is_bound(parameter: dict) -> bool:
    return parameter["source"]["type"] != "ai"


def _typed(value: object, kind: str) -> object:
    """Значение в типе параметра; ``_MISSING`` — его нет или тип не тот."""
    if kind == "boolean":
        return value if type(value) is bool else _MISSING
    if kind == "number":
        if isinstance(value, str) and _NUMBER.match(value.strip()):
            text = value.strip()
            value = float(text) if "." in text else int(text)
        if type(value) is int and value.bit_length() <= 1024:
            return value
        return value if type(value) is float and math.isfinite(value) else _MISSING
    # Номер заказа модель и сайт нередко присылают числом.
    if type(value) in (int, float):
        value = _typed(value, "number")
        value = _MISSING if value is _MISSING else _text(value)
    if not isinstance(value, str):
        return _MISSING
    value = value.strip()
    return value if value and len(value) <= MAX_VALUE_LENGTH else _MISSING


def _text(value: object) -> str:
    """Значение для адреса и query."""
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is float and value.is_integer():
        return str(int(value))
    return str(value)


def _client_value(source: dict, client: ClientData) -> object:
    if source["type"] == "contact":
        return getattr(client, source["field"]) if source.get("field") in CONTACT_FIELDS else _MISSING
    fields = client.web_fields.get(source.get("integration_id"), {})
    return fields.get(source.get("key"), _MISSING)


def input_schema(config: dict) -> dict:
    """Схема параметров для модели: только те, что она заполняет сама."""
    properties: dict[str, dict] = {}
    required: list[str] = []
    for parameter in _parameters(config):
        if _is_bound(parameter):
            continue
        described = {"type": parameter["type"]}
        if parameter.get("description"):
            described["description"] = parameter["description"]
        properties[parameter["name"]] = described
        if parameter.get("required"):
            required.append(parameter["name"])
    return {"type": "object", "properties": properties, "required": required}


def bound_arguments(config: dict, client: ClientData) -> dict[str, object] | None:
    """Значения привязанных параметров; None — обязательного нет, инструмент не предлагать."""
    values: dict[str, object] = {}
    for parameter in _parameters(config):
        if not _is_bound(parameter):
            continue
        value = _typed(_client_value(parameter["source"], client), parameter["type"])
        if value is not _MISSING:
            values[parameter["name"]] = value
        elif parameter.get("required"):
            return None
    return values


def _model_arguments(config: dict, arguments: Mapping[str, object]) -> dict[str, object]:
    values: dict[str, object] = {}
    for parameter in _parameters(config):
        if _is_bound(parameter):
            continue
        name = parameter["name"]
        raw = arguments.get(name)
        # Пустую строку модели шлют вместо пропуска необязательного параметра.
        if raw is None or raw == "":
            if parameter.get("required"):
                raise ToolArgumentsRejected(name)
            continue
        value = _typed(raw, parameter["type"])
        if value is _MISSING:
            raise ToolArgumentsRejected(name)
        values[name] = value
    return values


def _same_server(url: str, template: str) -> bool:
    try:
        final, expected = urlsplit(url), urlsplit(template_probe_url(template))
    except ValueError:
        return False
    return (final.scheme.lower(), final.netloc.lower()) == (
        expected.scheme.lower(),
        expected.netloc.lower(),
    )


def _request_headers(integration: Integration, *, with_body: bool) -> dict[str, str]:
    headers = request_headers(integration)
    if with_body:
        headers = {name: value for name, value in headers.items() if name.lower() != "content-type"}
        headers["Content-Type"] = "application/json"
    if not any(name.lower() == "accept" for name in headers):
        headers["Accept"] = "application/json, text/*"
    return headers


def build_request(
    integration: Integration, arguments: Mapping[str, object], bound: Mapping[str, object]
) -> HttpToolRequest:
    """Собрать запрос: аргументы модели и привязанные значения (``bound_arguments``).

    Аргумент не того типа или без обязательного значения —
    ``ToolArgumentsRejected``; аргументы мимо параметров отбрасываются, а
    привязанный параметр модель переопределить не может.
    """
    config = integration.config
    values = {**_model_arguments(config, arguments), **bound}
    template = str(config.get("url", ""))
    method = str(config.get("method", "GET"))
    url = template
    query: list[tuple[str, str]] = []
    body: dict[str, object] = {}
    for parameter in _parameters(config):
        name = parameter["name"]
        if name not in values:
            continue
        if parameter["location"] == "path":
            text = _text(values[name])
            # «.» и «..» сервер свернёт и уведёт запрос на другой путь.
            if text in (".", ".."):
                raise ToolArgumentsRejected(name)
            url = url.replace(f"{{{name}}}", quote(text, safe=""))
        elif parameter["location"] == "query":
            query.append((name, _text(values[name])))
        else:
            body[name] = values[name]
    # Сервер задан шаблоном: значение параметра его не меняет.
    if not _same_server(url, template):
        raise ToolAddressRejected("internal", t("integrations.tool_address_local"))
    parts = urlsplit(url)
    if query:
        parts = parts._replace(query="&".join(filter(None, [parts.query, urlencode(query)])))
    with_body = method in BODY_METHODS and (method != "DELETE" or bool(body))
    return HttpToolRequest(
        method=method,
        url=parts._replace(fragment="").geturl(),
        headers=_request_headers(integration, with_body=with_body),
        body=json.dumps(body, ensure_ascii=False).encode() if with_body else None,
    )


def call_http_tool(
    integration: Integration,
    arguments: Mapping[str, object],
    bound: Mapping[str, object],
    *,
    timeout: float,
) -> ToolResponse:
    """Выполнить запрос инструмента; отказы и сетевые ошибки — как у ``fetch``."""
    request = build_request(integration, arguments, bound)
    reads = request.method in READ_METHODS or request.method == "POST" and integration.config.get("read_only")
    return fetch(
        request.url,
        timeout=timeout,
        method=request.method,
        headers=request.headers,
        body=request.body,
        **({"same_origin_only": True} if not reads else {}),
    )
