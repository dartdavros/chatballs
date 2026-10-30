"""JSON Schema инструментов внешних серверов → общие типы контракта (SPEC-0037 R-4).

MCP-сервер и старый HTTP-запрос описывают параметры JSON Schema. Для общего
реестра она переводится в ``TypeSpec``: объекты, списки, перечисления,
nullable и даты сохраняются; неизвестное становится строкой, а не теряется.
"""

from __future__ import annotations

from typing import Any

from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

_SIMPLE = {"string": "string", "integer": "integer", "number": "number", "boolean": "boolean"}
_FORMATS = {"date": "date", "date-time": "datetime"}


def typespec_from_json_schema(schema: Any, *, required: bool = False) -> TypeSpec:
    if not isinstance(schema, dict):
        return TypeSpec("string", required=required)
    kind = schema.get("type")
    nullable = False
    if isinstance(kind, list):
        nullable = "null" in kind
        kind = next((item for item in kind if item != "null"), "string")
    if isinstance(schema.get("enum"), list) and schema["enum"]:
        options = tuple(EnumOption(value, "") for value in schema["enum"] if value is not None)
        return TypeSpec("enum", options=options, required=required, nullable=nullable or None in schema["enum"])
    if kind == "object" or (kind is None and isinstance(schema.get("properties"), dict)):
        must = set(schema.get("required") or [])
        properties = tuple(
            (name, typespec_from_json_schema(child, required=name in must))
            for name, child in (schema.get("properties") or {}).items()
        )
        is_open = schema.get("additionalProperties") is not False
        return TypeSpec("object", properties=properties, open=is_open, required=required, nullable=nullable)
    if kind == "array":
        return TypeSpec(
            "array", items=typespec_from_json_schema(schema.get("items")), required=required, nullable=nullable
        )
    if kind == "string" and schema.get("format") in _FORMATS:
        return TypeSpec(_FORMATS[schema["format"]], required=required, nullable=nullable)
    return TypeSpec(_SIMPLE.get(str(kind), "string"), required=required, nullable=nullable)
