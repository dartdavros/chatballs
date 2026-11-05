"""Типы параметров и результатов операций (SPEC-0037 R-4).

Схема описывает данные конкретного сервиса как есть: вложенные объекты,
списки, обязательность и nullable, перечисления, даты, справочники и ссылки на
файлы. Общей CRM-модели здесь нет — поля называет адаптер.

Значения в схеме — то, что ходит в JSON: даты строкой ISO 8601, файл —
``{"fileId": "<uuid>"}``, значение справочника — его идентификатор.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from chatballs.integrations.adapters.json_values import valid_json

SCALAR_TYPES = frozenset({"string", "integer", "number", "boolean", "date", "datetime"})
TYPES = SCALAR_TYPES | frozenset({"object", "array", "enum", "lookup", "file", "json"})


class SchemaDefinitionError(ValueError):
    """Схема в описании адаптера составлена неверно: ошибка разработчика."""


@dataclass(frozen=True)
class EnumOption:
    value: str | int | float | bool
    label_key: str


@dataclass(frozen=True)
class TypeSpec:
    type: str
    title_key: str = ""
    hint_key: str = ""
    placeholder_key: str = ""
    # Обязательность — свойство поля внутри объекта.
    required: bool = False
    nullable: bool = False
    properties: tuple[tuple[str, TypeSpec], ...] = ()
    # Объект допускает поля сверх описанных (ответ чужого API как есть).
    open: bool = False
    items: TypeSpec | None = None
    min_items: int | None = None
    max_items: int | None = None
    options: tuple[EnumOption, ...] = ()
    lookup: str = ""
    pattern: str = ""
    pattern_error_key: str = ""
    max_length: int | None = None
    # Ключ UI-контрола из реестра расширений; пусто — контрол по типу.
    control: str = ""
    secret: bool = False
    default: Any = None

    def field(self, name: str) -> TypeSpec | None:
        return dict(self.properties).get(name)


@dataclass(frozen=True)
class SchemaIssue:
    path: str
    code: str


@dataclass
class _Walk:
    issues: list[SchemaIssue] = field(default_factory=list)

    def add(self, path: str, code: str) -> None:
        self.issues.append(SchemaIssue(path or "$", code))


def validate_spec(spec: TypeSpec, path: str = "") -> None:
    """Проверить саму схему: известные типы и полнота составных типов."""

    where = path or "$"
    if spec.type not in TYPES:
        raise SchemaDefinitionError(f"{where}: unknown type {spec.type!r}")
    if spec.type == "object":
        names = [name for name, _child in spec.properties]
        if len(names) != len(set(names)):
            raise SchemaDefinitionError(f"{where}: duplicate property")
        for name, child in spec.properties:
            validate_spec(child, f"{path}.{name}" if path else name)
    if spec.type == "array":
        if spec.items is None:
            raise SchemaDefinitionError(f"{where}: array without items")
        validate_spec(spec.items, f"{path}[]")
    if spec.type == "enum" and not spec.options:
        raise SchemaDefinitionError(f"{where}: enum without options")
    if spec.type == "lookup" and not spec.lookup:
        raise SchemaDefinitionError(f"{where}: lookup without key")
    if spec.pattern:
        try:
            re.compile(spec.pattern)
        except re.error as error:
            raise SchemaDefinitionError(f"{where}: bad pattern") from error


def validate_value(spec: TypeSpec, value: Any) -> list[SchemaIssue]:
    """Ошибки значения по схеме; пустой список — значение подходит."""

    walk = _Walk()
    _check(spec, value, "", walk)
    return walk.issues


def _check(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if value is None:
        if not spec.nullable:
            walk.add(path, "null")
        return
    checker = _CHECKERS[spec.type]
    checker(spec, value, path, walk)


def _check_object(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if not isinstance(value, dict):
        walk.add(path, "type")
        return
    known = dict(spec.properties)
    for name in value:
        if name not in known and not spec.open:
            walk.add(_join(path, name), "unknown")
    for name, child in spec.properties:
        child_path = _join(path, name)
        # Обязательное — значит заданное: null допустим только у nullable,
        # пустая строка обязательное поле не заполняет.
        if name not in value or (value[name] is not None and _blank(value[name])):
            if child.required:
                walk.add(child_path, "required")
            continue
        _check(child, value[name], child_path, walk)


def _check_array(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if not isinstance(value, list):
        walk.add(path, "type")
        return
    if spec.min_items is not None and len(value) < spec.min_items:
        walk.add(path, "min_items")
    if spec.max_items is not None and len(value) > spec.max_items:
        walk.add(path, "max_items")
    assert spec.items is not None
    for index, item in enumerate(value):
        _check(spec.items, item, f"{path}[{index}]", walk)


def _check_string(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if not isinstance(value, str):
        walk.add(path, "type")
        return
    if spec.max_length is not None and len(value) > spec.max_length:
        walk.add(path, "max_length")
    if spec.pattern and not re.fullmatch(spec.pattern, value.strip()):
        walk.add(path, "pattern")


def _check_integer(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        walk.add(path, "type")


def _check_number(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        walk.add(path, "type")


def _check_boolean(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if not isinstance(value, bool):
        walk.add(path, "type")


def _check_date(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if not isinstance(value, str):
        walk.add(path, "type")
        return
    parser = date.fromisoformat if spec.type == "date" else datetime.fromisoformat
    try:
        parser(value)
    except ValueError:
        walk.add(path, "type")


def _check_enum(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if not any(type(value) is type(option.value) and value == option.value for option in spec.options):
        walk.add(path, "choice")


def _check_lookup(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if isinstance(value, bool) or not isinstance(value, str | int) or value == "":
        walk.add(path, "type")


def _check_file(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    file_id = value.get("fileId") if isinstance(value, dict) else None
    try:
        uuid.UUID(str(file_id))
    except ValueError:
        walk.add(path, "type")
        return
    if set(value) != {"fileId"}:
        walk.add(path, "unknown")


def _check_json(spec: TypeSpec, value: Any, path: str, walk: _Walk) -> None:
    if not valid_json(value):
        walk.add(path, "type")


_CHECKERS = {
    "json": _check_json,
    "object": _check_object,
    "array": _check_array,
    "string": _check_string,
    "integer": _check_integer,
    "number": _check_number,
    "boolean": _check_boolean,
    "date": _check_date,
    "datetime": _check_date,
    "enum": _check_enum,
    "lookup": _check_lookup,
    "file": _check_file,
}


def _join(path: str, name: str) -> str:
    return f"{path}.{name}" if path else name


def _blank(value: Any) -> bool:
    return isinstance(value, str) and not value.strip()
