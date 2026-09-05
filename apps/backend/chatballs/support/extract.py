"""Извлечение identity/operator/ai/search контекста по контракту (SPEC-HUB-0011 §6-11).

Валидация payload по schema_json — ручная (нет jsonschema-зависимости):
проверка required-полей object и вложенных object-properties, pattern из orders/views.py.
Глубокая type-проверка — TODO.
"""

from __future__ import annotations

from typing import Any

from chatballs.support import errors, jsonpath
from chatballs.support.models import ProductSupportContract


def validate_schema(data: dict[str, Any], schema: dict[str, Any]) -> None:
    """Ручная проверка required-полей по schema. Поднимает PAYLOAD_SCHEMA_INVALID."""
    if not schema:
        return
    required = schema.get("required") or []
    if isinstance(required, list):
        for field in required:
            if field not in data:
                raise errors.SupportSessionError(errors.PAYLOAD_SCHEMA_INVALID)
    # Рекурсивная проверка required во вложенных object-properties.
    properties = schema.get("properties") or {}
    if isinstance(properties, dict):
        for field, subschema in properties.items():
            if not isinstance(subschema, dict):
                continue
            sub_required = subschema.get("required")
            value = data.get(field)
            if isinstance(sub_required, list) and isinstance(value, dict):
                for sub_field in sub_required:
                    if sub_field not in value:
                        raise errors.SupportSessionError(errors.PAYLOAD_SCHEMA_INVALID)


def extract_context(data: dict[str, Any], contract: ProductSupportContract) -> dict[str, Any]:
    """Извлекает identity/operator_cards/ai_context/search по mapping'ам контракта."""
    identity = contract.identity_mapping_json or {}
    subject = jsonpath.resolve_path(data, identity.get("subject", ""))
    if not subject:
        raise errors.SupportSessionError(errors.SUBJECT_MAPPING_EMPTY)

    account = jsonpath.resolve_path(data, identity.get("account", ""))
    display_name = jsonpath.resolve_path(data, identity.get("display_name", "")) or ""
    display_email = jsonpath.resolve_path(data, identity.get("display_email", "")) or ""

    operator_cards = build_operator_cards(data, contract.operator_ui_json or {})
    ai_context = build_ai_context(data, contract.ai_context_json or {})
    search_text = build_search_text(data, contract.search_mapping_json or {})

    return {
        "subject_key": str(subject),
        "account_key": str(account) if account else "",
        "display_name": str(display_name),
        "display_email": str(display_email),
        "operator_context": {"operator_cards": operator_cards},
        "ai_context": ai_context,
        "search_text": search_text,
    }


def build_operator_cards(data: dict[str, Any], ui: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for card in ui.get("operator_cards", []) or []:
        fields = []
        for field in card.get("fields", []) or []:
            value = jsonpath.resolve_path(data, field.get("path", ""))
            fields.append(
                {
                    "label": field.get("label", ""),
                    "value": value,
                    "type": field.get("type", "text"),
                    "visibility": field.get("visibility", "operator"),
                }
            )
        cards.append({"title": card.get("title", ""), "fields": fields})
    return cards


def build_ai_context(data: dict[str, Any], ai: dict[str, Any]) -> dict[str, Any]:
    allowed = ai.get("allowed_paths", []) or []
    values: dict[str, Any] = {}
    for path in allowed:
        values[path] = jsonpath.resolve_path(data, path)
    return {"allowed_paths": values}


def build_search_text(data: dict[str, Any], search: dict[str, Any]) -> str:
    paths = search.get("paths", []) or []
    parts = [str(jsonpath.resolve_path(data, p)) for p in paths]
    return " ".join(p for p in parts if p and p != "None")
