"""Bounded, flat site data: values are never instructions or resource identities."""

import json
import math
import re

from django.core.exceptions import ValidationError

from chatballs.i18n import t

NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9_.-]{0,79}\Z")
FIELD = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
MAX_ENVELOPE_BYTES = 20 * 1024
MAX_FIELDS = 30
MAX_TEXT = 4000


def reject():
    # Do not include a submitted name, field, value or schema in the error.
    raise ValidationError({"siteEvent": t("site_events.invalid")})


def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def normalize_schema(raw):
    if not isinstance(raw, list) or len(raw) > MAX_FIELDS:
        reject()
    fields, seen = [], set()
    for item in raw:
        if not isinstance(item, dict):
            reject()
        name, kind = item.get("name"), item.get("type")
        if not isinstance(name, str) or not FIELD.fullmatch(name) or name in seen:
            reject()
        if kind not in {"string", "number", "boolean"} or type(item.get("required", False)) is not bool:
            reject()
        seen.add(name)
        allowed = {"name", "type", "required"}
        field = {"name": name, "type": kind, "required": item.get("required", False)}
        if kind == "string":
            allowed.add("maxLength")
            limit = item.get("maxLength")
            if type(limit) is not int or not 1 <= limit <= MAX_TEXT:
                reject()
            field["maxLength"] = limit
        elif kind == "number":
            allowed.update({"minimum", "maximum"})
            low, high = item.get("minimum"), item.get("maximum")
            if not finite(low) or not finite(high) or low > high:
                reject()
            field.update(minimum=low, maximum=high)
        if set(item) - allowed:
            reject()
        fields.append(field)
    return fields


def validate_data(schema, data):
    if not isinstance(data, dict) or set(data) - {f["name"] for f in schema}:
        reject()
    for field in schema:
        name = field["name"]
        if name not in data:
            if field["required"]:
                reject()
            continue
        value, kind = data[name], field["type"]
        if kind == "string" and (not isinstance(value, str) or len(value) > field["maxLength"]):
            reject()
        if kind == "number" and (not finite(value) or not field["minimum"] <= value <= field["maximum"]):
            reject()
        if kind == "boolean" and type(value) is not bool:
            reject()


def validate_envelope(value):
    if not isinstance(value, dict) or set(value) != {"name", "eventId", "data"}:
        reject()
    if not isinstance(value["name"], str) or not NAME.fullmatch(value["name"]):
        reject()
    event_id = value["eventId"]
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 200 or not event_id.strip():
        reject()
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    except (TypeError, ValueError, OverflowError):
        reject()
    if len(encoded) > MAX_ENVELOPE_BYTES:
        reject()
