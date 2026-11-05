"""Lossless typed scalar choices for heterogeneous quality scales."""

from copy import deepcopy

from rest_framework.exceptions import ValidationError

from chatballs.i18n import t


def encode(value):
    if value is None:
        return None
    return {{str: "textValue", int: "integerValue", float: "numberValue"}[type(value)]: value}


def decode(value):
    if not isinstance(value, dict) or len(value) != 1 or not set(value) <= {"textValue", "integerValue", "numberValue"}:
        raise ValidationError(t("quality.criteria_invalid"))
    key, scalar = next(iter(value.items()))
    return float(scalar) if key == "numberValue" else scalar


def criteria(rows, *, writing=False):
    rows = deepcopy(rows)
    for row in rows:
        row["scale"] = [(decode if writing else encode)(value) for value in row["scale"]]
    return rows


def settings_payload(payload):
    payload = deepcopy(payload)
    payload["criteria"] = criteria(payload["criteria"])
    if payload["suggestedCriteria"] is not None:
        payload["suggestedCriteria"] = criteria(payload["suggestedCriteria"])
    for scale in payload["scales"]:
        scale["values"] = [encode(value) for value in scale["values"]]
    return payload


def job_payload(payload):
    payload = deepcopy(payload)
    payload["state"] = str(payload["state"])
    payload["criteria"] = criteria(payload["criteria"])
    for row in payload["conclusions"]:
        for key in ("originalValue", "effectiveValue"):
            row[key] = encode(row[key])
    for row in payload["corrections"]:
        row["value"] = encode(row["value"])
    return payload
