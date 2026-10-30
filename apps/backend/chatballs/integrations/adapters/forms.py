"""Тела форм для HTTP-операций: вложенные поля и файлы (SPEC-0037 R-4, R-5).

Многие API принимают вложенные данные формой в нотации ``a[b][0][c]``;
файл в теле — ссылка ``{"fileId": ...}`` на штатное хранилище, байты
читаются только в момент отправки.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

OpenFile = Callable[[str], tuple[str, str, bytes]]


def flatten_form(values: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for name, value in values.items():
        key = f"{prefix}[{name}]" if prefix else str(name)
        pairs.extend(_flatten(key, value))
    return pairs


def _flatten(key: str, value: Any) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        return flatten_form(value, key)
    if isinstance(value, list):
        pairs: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            pairs.extend(_flatten(f"{key}[{index}]", item))
        return pairs
    if value is None:
        return [(key, "")]
    if isinstance(value, bool):
        return [(key, "Y" if value else "N")]
    return [(key, str(value))]


def multipart_body(values: dict[str, Any], open_file: OpenFile | None) -> tuple[str, bytes]:
    boundary = f"chatballs-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in values.items():
        if isinstance(value, dict) and set(value) == {"fileId"}:
            if open_file is None:
                raise ValueError(name)
            filename, content_type, content = open_file(str(value["fileId"]))
            header = (
                f'Content-Disposition: form-data; name="{_quoted(name)}"; filename="{_quoted(filename)}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            )
            parts.append(f"--{boundary}\r\n{header}".encode() + content + b"\r\n")
            continue
        for key, text in _flatten(str(name), value):
            header = f'Content-Disposition: form-data; name="{_quoted(key)}"\r\n\r\n'
            parts.append(f"--{boundary}\r\n{header}{text}\r\n".encode())
    parts.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


def _quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "")
