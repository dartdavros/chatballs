"""Exact typed canonicalization from the accepted OpenAPI v1 contract."""

import hashlib
import hmac
import json
from decimal import Decimal


def _invalid(_value):
    raise ValueError("invalid_request")


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("invalid_request")
        value[key] = item
    return value


def decode(body: bytes):
    if len(body) > 262144:
        raise ValueError("payload_too_large")
    try:
        value = json.loads(body, parse_float=Decimal, parse_int=int,
                           parse_constant=_invalid, object_pairs_hook=_object)
        _unicode(value)
        return value
    except (UnicodeError, RecursionError) as error:
        raise ValueError("invalid_request") from error


def _unicode(value, depth=0):
    if depth > 64:
        raise ValueError("invalid_request")
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif isinstance(value, dict):
        for key, item in value.items():
            _unicode(key, depth + 1)
            _unicode(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _unicode(item, depth + 1)


def _number(value):
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError("invalid_request")
    if not number:
        return "0e0"
    sign, digits, exponent = number.as_tuple()
    coefficient = "".join(map(str, digits)).lstrip("0")
    while coefficient.endswith("0"):
        coefficient = coefficient[:-1]
        exponent += 1
    return f"{'-' if sign else ''}{coefficient}e{exponent}"


def tree(value):
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["boolean", value]
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
        return ["string", value]
    if type(value) in (int, Decimal):
        return ["number", _number(value)]
    if isinstance(value, list):
        return ["array", [tree(item) for item in value]]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return ["object", [[key, tree(value[key])] for key in sorted(value)]]
    # A float has already lost information; never silently accept it here.
    raise ValueError("invalid_request")


def canonical_bytes(value):
    return json.dumps(tree(value), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(key: str, *, operation: str, route: list, body):
    value = {"operation": operation, "route": route, "body": body}
    return hmac.new(key.encode(), canonical_bytes(value), hashlib.sha256).hexdigest()
