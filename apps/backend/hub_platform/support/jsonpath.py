"""Ограниченный JSONPath-subset для mapping'ов контракта (SPEC-HUB-0011 §6).

Допускаются только:
  $.field
  $.field.nested
  $.array[0].field  — только целочисленный индекс, без filters/scripts

Произвольные expressions, filters или script-like expressions не допускаются.
Отсутствующий обязательный path обрабатывается вызывающей стороной (subject).
"""

from __future__ import annotations

from typing import Any

_MISSING = object()

# Унификация: принимаем как "$.a.b", так и "a.b" (без префикса).
_PREFIX = "$."


def _normalize(path: str) -> str:
    if path.startswith(_PREFIX):
        return path[len(_PREFIX):]
    return path


def resolve_path(data: Any, path: str) -> Any:
    """Возвращает значение по path или None, если path отсутствует.

    None для optional paths; вызывающая сторона решает, обязателен ли path.
    Некорректный path (не массив по индексу и т.п.) тоже даёт None — контракт
    не должен ронять renderer на отсутствующих optional полях (SPEC §6).
    """
    if not path or not isinstance(data, dict | list):
        return None
    current: Any = data
    for segment in _normalize(path).split("."):
        if segment == "":
            continue
        # Поддержка array[0] внутри сегмента: field[2]
        idx = _array_index(segment)
        if idx is not None:
            name = segment.split("[", 1)[0]
            current = _step(current, name)
            if current is _MISSING:
                return None
            current = _index(current, idx)
            if current is _MISSING:
                return None
        else:
            current = _step(current, segment)
            if current is _MISSING:
                return None
    return None if current is _MISSING else current


def _step(current: Any, name: str) -> Any:
    if isinstance(current, dict):
        return current.get(name, _MISSING)
    return _MISSING


def _index(current: Any, idx: int) -> Any:
    if isinstance(current, list) and -len(current) <= idx < len(current):
        return current[idx]
    return _MISSING


def _array_index(segment: str) -> int | None:
    if "[" not in segment or not segment.endswith("]"):
        return None
    inner = segment[segment.index("[") + 1 : -1]
    if not inner.lstrip("-").isdigit():
        return None
    return int(inner)
