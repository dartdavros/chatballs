"""Ответы API сервисов: каталог из описаний адаптеров и подключения без секретов.

Общий интерфейс получает тексты, поля и готовые сценарии из адаптера и не
знает названий сервисов. Credentials наружу не уходят: только признак, что
они сохранены, и хост, который из них не секретен.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Any

from chatballs.i18n import t
from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    ScenarioTemplate,
)
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.models import (
    Integration,
    IntegrationStatus,
    OAuthStateStatus,
    ServiceOAuthState,
)
from chatballs.integrations.service_connections.binding import (
    ServiceUnavailable,
    load_credentials,
    resolve,
)
from chatballs.integrations.service_connections.errors import error_payload
from chatballs.integrations.service_connections.services import OAUTH_EXTENSION

_STATUS = {IntegrationStatus.OK: "ok", IntegrationStatus.ERROR: "lost", IntegrationStatus.UNCHECKED: "unchecked"}


def _text(key: str) -> str:
    return t(key) if key else ""


def field_payload(name: str, spec: TypeSpec) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "type": spec.type,
        "title": _text(spec.title_key) or name,
        "hint": _text(spec.hint_key),
        "placeholder": _text(spec.placeholder_key),
        "required": spec.required,
        "nullable": spec.nullable,
        "open": spec.open,
        "secret": spec.secret,
        "control": spec.control,
        "maxLength": spec.max_length,
        "minItems": spec.min_items,
        "maxItems": spec.max_items,
    }
    if spec.pattern:
        payload["pattern"] = spec.pattern
        payload["patternError"] = _text(spec.pattern_error_key)
    if spec.options:
        payload["options"] = [{"value": option.value, "label": _text(option.label_key) or str(option.value)} for option in spec.options]
    if spec.lookup:
        payload["lookup"] = spec.lookup
    if spec.properties:
        payload["fields"] = fields_payload(spec)
    if spec.items is not None:
        payload["items"] = field_payload("", spec.items)
    return payload


def fields_payload(spec: TypeSpec) -> list[dict[str, Any]]:
    return [field_payload(name, child) for name, child in spec.properties]


def _auth_payload(method: AuthMethod) -> dict[str, Any]:
    check = method.check
    return {
        "key": method.key,
        "title": _text(method.title_key),
        "about": _text(method.about_key),
        "note": _text(method.note_key),
        "accessLabel": _text(method.access_label_key),
        "savedLabel": _text(method.saved_label_key),
        "oauth": method.extension == OAUTH_EXTENSION,
        "checkable": check is not None,
        "checkNote": _text(check.note_key) if check else "",
        "checkInputs": fields_payload(check.inputs) if check and check.inputs else None,
        "fields": fields_payload(method.fields),
    }


def template_payload(template: ScenarioTemplate) -> dict[str, Any]:
    return {
        "key": template.key,
        "version": template.version,
        "title": _text(template.title_key),
        "purpose": _text(template.purpose_key),
        "requiredConnections": list(template.required_connections),
        "requiredPermissions": list(template.required_permissions),
        "parameters": fields_payload(template.parameters),
        "triggers": list(template.triggers),
        "conditions": list(template.conditions),
        "steps": [{"id": step.id, "title": _text(step.title_key), "target": step.target, "inputs": step.inputs} for step in template.steps],
    }


def adapter_payload(adapter: AdapterDescriptor) -> dict[str, Any]:
    presentation = adapter.presentation
    help_block = presentation.help
    return {
        "key": adapter.key,
        "version": adapter.contract_version,
        "title": _text(presentation.title_key),
        "about": _text(presentation.about_key),
        "connectLead": _text(presentation.connect_lead_key),
        "hostLabel": _text(presentation.host_label_key),
        "logo": {
            "light": _logo(adapter.package_dir, presentation.logo_light),
            "dark": _logo(adapter.package_dir, presentation.logo_dark),
        },
        "help": {
            "title": _text(help_block.title_key),
            "steps": [_text(key) for key in help_block.steps],
            "paragraphs": [_text(key) for key in help_block.paragraphs],
            "link": _text(help_block.link_key),
            "url": _text(help_block.link_url_key),
        } if help_block else None,
        "authMethods": [_auth_payload(method) for method in adapter.auth_methods],
        "settings": fields_payload(adapter.settings),
        "operations": [
            {
                "key": operation.key,
                "title": _text(operation.title_key),
                "effect": operation.effect.value,
                "mode": operation.mode.value,
                "retry": operation.retry.value,
                "cancellable": operation.cancellable,
                "permissionScope": operation.permission_scope,
                "entityKind": operation.entity_kind,
                "input": field_payload("", operation.input),
                "output": field_payload("", operation.output),
            }
            for operation in adapter.operations
        ],
        "lookups": [{"key": lookup.key, "title": _text(lookup.title_key)} for lookup in adapter.lookups],
        "entities": [{"key": entity.key, "title": _text(entity.title_key), "fields": field_payload("", entity.fields),
                      "synchronization": synchronization_payload(entity.synchronization),
                      "nativeEntities": list(entity.native_entities)} for entity in adapter.entities],
        "events": [{"key": event.key, "title": _text(event.title_key), "delivery": event.delivery.value,
                    "payload": field_payload("", event.payload)} for event in adapter.events],
        "unsupported": [{"capability": item.capability, "reason": _text(item.reason_key)} for item in adapter.unsupported],
        "presets": [template_payload(template) for template in adapter.templates],
    }


def synchronization_payload(binding):
    if binding is None:
        return {"directions": [], "deletion": ["unlink", "keep"]}
    return {"directions": ["reverse"] + (["forward", "both"] if binding.update_operation else []),
            "deletion": ["unlink", "keep"] + (["propagate"] if binding.delete_operation else [])}


def catalog_payload() -> list[dict[str, Any]]:
    return [adapter_payload(adapter) for adapter in default_registry().catalog()]


def connection_payload(integration: Integration) -> dict[str, Any]:
    row = integration.service_settings
    adapter = default_registry().adapter(row.adapter_key)
    incompatible = False
    host = ""
    try:
        _row, adapter, method = resolve(integration)
        auth = default_registry().extension("auth", method.extension).implementation
        host = auth.host(row.settings, load_credentials(row), method.options)
    except ServiceUnavailable:
        incompatible = True
    status = _STATUS.get(integration.status, "unchecked")
    return {
        "id": integration.id,
        "name": integration.name,
        "adapter": row.adapter_key,
        "authMethod": row.auth_method,
        "status": status,
        "isActive": integration.is_active,
        "host": host,
        "hasCredentials": bool(row.credentials),
        "incompatible": incompatible,
        "lastCheckedAt": integration.last_checked_at.isoformat() if integration.last_checked_at else None,
        "error": error_payload(adapter, integration.last_error_code).as_dict() if status == "lost" else None,
        # Сценарии подключения появятся вместе с их редактором.
        "scenarios": {"enabled": integration.scenarios.filter(scenario__enabled=True).count()},
        "createdAt": integration.created_at.isoformat(),
    }


def oauth_state_payload(state: ServiceOAuthState) -> dict[str, Any]:
    adapter = default_registry().adapter(state.adapter_key)
    failed = state.status in (OAuthStateStatus.DENIED, OAuthStateStatus.FAILED)
    code = state.error_code or "rejected"
    error = None
    if failed:
        error = (
            {"code": code, "title": t("services.oauth_denied_title"), "text": t("services.oauth_denied_text")}
            if code == "oauth_denied" else error_payload(adapter, code).as_dict()
        )
    return {
        "id": str(state.public_id),
        "status": state.status.lower(),
        "connectionId": state.result_id,
        "error": error,
    }


@lru_cache(maxsize=64)
def _logo(package_dir: str, name: str) -> str:
    if not package_dir or not name:
        return ""
    path = Path(package_dir) / name
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{data}"
