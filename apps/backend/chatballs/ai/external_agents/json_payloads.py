"""JSON transport/storage encoding without rounding PostgreSQL JSON numbers."""

import json
from decimal import Decimal


def dumps(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("invalid_request")
        return str(value)
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(key, ensure_ascii=False) + ":" + dumps(item)
                              for key, item in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(dumps(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def loads(value):
    return json.loads(value, parse_float=Decimal)


def size(value):
    return len(dumps(value).encode("utf-8"))
