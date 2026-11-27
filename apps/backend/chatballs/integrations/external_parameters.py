"""Параметры HTTP-запроса и источник их значения (SPEC-0023 R-3, R-4).

Значение параметра заполняет модель («ai») либо подставляет сервер из данных
клиента: имени, e-mail или телефона контакта («contact») или своего поля
веб-подключения («web_field»). Привязанный параметр модели не показывается.
"""

from __future__ import annotations

import re

from chatballs.identity.models import Organization
from chatballs.integrations.external_errors import SettingsErrors
from chatballs.integrations.http_methods import BODY_METHODS
from chatballs.integrations.models import Integration, IntegrationProvider

MAX_PARAMETERS = 20
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")
PARAMETER_TYPES = ("string", "number", "boolean")
LOCATIONS = ("path", "query", "body")
CONTACT_FIELDS = ("name", "email", "phone")


def _web_field_exists(organization: Organization, integration_id: object, key: str) -> bool:
    if isinstance(integration_id, bool) or not isinstance(integration_id, int):
        return False
    web = Integration.objects.filter(
        organization=organization, provider=IntegrationProvider.WEB, id=integration_id
    ).first()
    fields = web.config.get("fields", []) if web else []
    return any(isinstance(field, dict) and field.get("key") == key for field in fields)


def _source(raw: object, *, organization: Organization) -> tuple[dict | None, str]:
    """Источник значения и ключ ошибки, если он задан неверно."""
    invalid = "integrations.tool_parameter_invalid"
    if raw is None:
        return {"type": "ai"}, ""
    if not isinstance(raw, dict):
        return None, invalid
    kind = raw.get("type")
    if kind == "ai":
        return {"type": "ai"}, ""
    if kind == "contact":
        field = raw.get("field")
        return ({"type": "contact", "field": field}, "") if field in CONTACT_FIELDS else (None, invalid)
    if kind == "web_field":
        integration_id = raw.get("integrationId", raw.get("integration_id"))
        key = str(raw.get("key") or "")
        if not _web_field_exists(organization, integration_id, key):
            return None, "integrations.tool_parameter_field_not_found"
        return {"type": "web_field", "integration_id": integration_id, "key": key}, ""
    return None, invalid


def submitted_names(submitted: object) -> set[str]:
    """Имена параметров из запроса — в том числе тех, что не прошли проверку."""
    if not isinstance(submitted, list):
        return set()
    return {str(item.get("name") or "").strip() for item in submitted if isinstance(item, dict)}


def normalize_parameters(
    submitted: object,
    *,
    method: str,
    placeholders: set[str],
    organization: Organization,
    errors: SettingsErrors,
) -> list[dict]:
    """Проверить параметры и привести к виду хранения.

    ``placeholders`` — имена подстановок из адреса: такой параметр передаётся
    в адресе и обязателен, без значения адрес не собрать.
    """
    if not isinstance(submitted, list):
        errors.add("parameters", "integrations.tool_parameter_invalid", name="")
        return []
    if len(submitted) > MAX_PARAMETERS:
        errors.add("parameters", "integrations.tool_parameters_limit", limit=MAX_PARAMETERS)
        return []
    parameters: list[dict] = []
    seen: set[str] = set()
    for raw in submitted:
        item = raw if isinstance(raw, dict) else {}
        name = str(item.get("name") or "").strip()
        if not NAME_PATTERN.match(name):
            errors.add("parameters", "integrations.tool_parameter_name_invalid", name=name)
            continue
        if name in seen:
            errors.add("parameters", "integrations.tool_parameter_duplicate", name=name)
            continue
        seen.add(name)
        in_url = name in placeholders
        location = "path" if in_url else item.get("location", "query")
        source, source_error = _source(item.get("source"), organization=organization)
        if item.get("type") not in PARAMETER_TYPES or location not in LOCATIONS:
            errors.add("parameters", "integrations.tool_parameter_invalid", name=name)
        elif location == "path" and not in_url:
            errors.add("parameters", "integrations.tool_parameter_not_in_url", name=name)
        elif location == "body" and method not in BODY_METHODS:
            errors.add("parameters", "integrations.tool_parameter_body_post_only", name=name)
        elif source is None:
            errors.add("parameters", source_error, name=name)
        else:
            parameters.append(
                {
                    "name": name,
                    "type": item["type"],
                    "description": str(item.get("description") or "").strip(),
                    "required": in_url or bool(item.get("required")),
                    "location": location,
                    "source": source,
                }
            )
    return parameters


def parameters_payload(stored: object) -> list[dict]:
    result = []
    for parameter in stored if isinstance(stored, list) else []:
        source = dict(parameter["source"])
        if "integration_id" in source:
            source["integrationId"] = source.pop("integration_id")
        result.append({**parameter, "source": source})
    return result
