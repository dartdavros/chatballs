"""Типизированные преобразования значений (SPEC-0037 R-10; ADR-0038 п.3).

Набор закрыт и исполняется сервером: пользовательский сценарий выбирает
преобразование по ключу и версии, произвольный код не исполняется. Каждое
преобразование объявляет типы входа и выхода, чтобы привязку можно было
проверить до эффекта.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from chatballs.integrations.adapters.registry import Extension
from chatballs.integrations.adapters.schema import TypeSpec


class TransformError(ValueError):
    """Значение не подходит преобразованию; ``code`` — причина без данных."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Transform:
    input_types: frozenset[str]
    output_type: str
    apply: Callable[..., Any]
    arguments: TypeSpec = TypeSpec("object")
    title_key: str = ""


def _text(value: Any) -> str:
    if not isinstance(value, str):
        raise TransformError("type")
    return value


def _number(value: Any) -> Decimal:
    try:
        return Decimal(str(value).replace(",", ".").strip())
    except ArithmeticError as error:
        raise TransformError("number") from error


def _round(value: Any, digits: int = 0) -> float:
    quantum = Decimal(1).scaleb(-int(digits))
    return float(_number(value).quantize(quantum, rounding=ROUND_HALF_UP))


def _parse_date(value: Any) -> str:
    try:
        return date.fromisoformat(_text(value).strip()[:10]).isoformat()
    except ValueError as error:
        raise TransformError("date") from error


def _parse_datetime(value: Any) -> str:
    try:
        return datetime.fromisoformat(_text(value).strip()).isoformat()
    except ValueError as error:
        raise TransformError("datetime") from error


def _list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise TransformError("type")
    return value


def _of_object(value: Any, key: str = "value", extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Значение → список из одного объекта: ``[{key: value, **extra}]``; пусто — пустой список."""

    if value is None or value == "":
        return []
    return [{key: value, **(extra or {})}]


def _get(value: Any, path: str = "") -> Any:
    current = value
    for part in [item for item in path.split(".") if item]:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


_TEXT = frozenset({"string"})
_ANY_SCALAR = frozenset({"string", "integer", "number"})

TRANSFORMS: dict[str, Transform] = {
    "text.stringify": Transform(_ANY_SCALAR, "string", lambda value: str(value)),
    "text.trim": Transform(_TEXT, "string", lambda value: _text(value).strip()),
    "text.lower": Transform(_TEXT, "string", lambda value: _text(value).lower()),
    "text.upper": Transform(_TEXT, "string", lambda value: _text(value).upper()),
    "text.concat": Transform(_TEXT, "string", lambda value, suffix="", prefix="": f"{prefix}{_text(value)}{suffix}"),
    "number.parse": Transform(_ANY_SCALAR, "number", lambda value: float(_number(value))),
    "number.round": Transform(_ANY_SCALAR, "number", _round),
    "date.parse": Transform(_TEXT, "date", _parse_date),
    "datetime.parse": Transform(_TEXT, "datetime", _parse_datetime),
    "list.join": Transform(frozenset({"array"}), "string", lambda value, separator=", ": separator.join(map(str, _list(value)))),
    "list.first": Transform(frozenset({"array"}), "any", lambda value: (_list(value) or [None])[0]),
    "list.of_object": Transform(_ANY_SCALAR, "array", _of_object),
    "list.count": Transform(frozenset({"array"}), "integer", lambda value: len(_list(value))),
    "object.get": Transform(frozenset({"object", "array"}), "any", _get),
}

_ARGUMENTS = {
    "text.concat": (("prefix", TypeSpec("string", title_key="scenarios.prefix")), ("suffix", TypeSpec("string", title_key="scenarios.suffix"))),
    "number.round": (("digits", TypeSpec("integer", title_key="scenarios.digits")),),
    "list.join": (("separator", TypeSpec("string", title_key="scenarios.separator")),),
    "object.get": (("path", TypeSpec("string", title_key="scenarios.field", required=True)),),
    "list.of_object": (("key", TypeSpec("string", title_key="scenarios.field", required=True)),
                       ("extra", TypeSpec("object", open=True, title_key="scenarios.extra_fields"))),
}


def builtin_extensions() -> list[Extension]:
    from dataclasses import replace
    return [Extension("transform", key, 1, replace(transform,
        title_key=f"scenarios.transform_{key.replace('.', '_')}",
        arguments=TypeSpec("object", properties=_ARGUMENTS.get(key, ())),
    )) for key, transform in TRANSFORMS.items()]
