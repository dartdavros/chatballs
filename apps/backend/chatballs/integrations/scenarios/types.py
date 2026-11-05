"""Persist TypeSpec semantics without translating an adapter into a CRM model."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from chatballs.integrations.adapters.schema import EnumOption, TypeSpec, validate_spec


def read_type(data: Any, depth: int = 0) -> TypeSpec:
    if depth > 16 or not isinstance(data, dict):
        raise ValueError("schema")
    allowed = {"type", "title", "required", "nullable", "properties", "items", "options", "lookup", "open"}
    if set(data) - allowed:
        raise ValueError("schema")
    if "title" in data and (not isinstance(data["title"], str) or len(data["title"]) > 200):
        raise ValueError("schema")
    if "lookup" in data and (not isinstance(data["lookup"], str) or len(data["lookup"]) > 100):
        raise ValueError("schema")
    properties = data.get("properties", {})
    if not isinstance(properties, dict) or len(properties) > 100:
        raise ValueError("schema")
    if any(not isinstance(key, str) or not key or len(key) > 100 for key in properties):
        raise ValueError("schema")
    options = data.get("options", [])
    if not isinstance(options, list) or any(type(v) not in (str, int, float, bool) for v in options):
        raise ValueError("schema")
    for flag in ("required", "nullable", "open"):
        if flag in data and not isinstance(data[flag], bool):
            raise ValueError("schema")
    spec = TypeSpec(
        type=data.get("type", ""), required=data.get("required", False), nullable=data.get("nullable", False),
        properties=tuple((key, read_type(value, depth + 1)) for key, value in properties.items()),
        items=read_type(data["items"], depth + 1) if "items" in data else None,
        options=tuple(EnumOption(v, "") for v in options), lookup=data.get("lookup", ""),
        open=data.get("open", False),
    )
    validate_spec(spec)
    return spec


def write_type(spec: TypeSpec) -> dict:
    result = {"type": spec.type, "required": spec.required, "nullable": spec.nullable}
    if spec.type == "object":
        result.update(properties={name: write_type(child) for name, child in spec.properties}, open=spec.open)
    if spec.items:
        result["items"] = write_type(spec.items)
    if spec.options:
        result["options"] = [option.value for option in spec.options]
    if spec.lookup:
        result["lookup"] = spec.lookup
    return result


def at_path(spec: TypeSpec | None, path: str) -> TypeSpec | None:
    if not isinstance(path, str):
        return None
    for part in filter(None, path.split(".")):
        if spec is None:
            return None
        if spec.type == "array" and part.isdecimal():
            spec = spec.items
        else:
            spec = spec.field(part)
    return spec


def compatible(source: TypeSpec, target: TypeSpec) -> bool:
    if source.nullable and not target.nullable:
        return False
    if target.type == "json":
        return True
    if source.type != target.type and not (source.type == "integer" and target.type == "number"):
        return False
    if target.type == "lookup":
        return source.lookup == target.lookup
    if target.type == "enum":
        return all(any(type(s.value) is type(t.value) and s.value == t.value for t in target.options) for s in source.options)
    if target.type == "array":
        return source.items is not None and target.items is not None and compatible(source.items, target.items)
    if target.type == "object":
        source_fields = dict(source.properties)
        for name, child in target.properties:
            found = source_fields.get(name)
            if found is None:
                if child.required:
                    return False
            elif (child.required and not found.required) or not compatible(found, child):
                return False
    return True


def optional(spec: TypeSpec) -> TypeSpec:
    return replace(spec, required=False)
