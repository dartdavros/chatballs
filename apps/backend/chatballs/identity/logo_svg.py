"""Проверка SVG-логотипа организации.

SVG — это XML с возможностью исполнять скрипты и тянуть внешние ресурсы.
Логотип отдаётся с адреса самого приложения, поэтому опасный файл принимать
нельзя даже с защитными заголовками при отдаче: файл проверяется при загрузке
и отклоняется целиком, а не «чистится» — переписывать чужую графику молча
хуже, чем попросить другой файл.

Отклоняется: DOCTYPE и сущности, элементы script/foreignObject/iframe/
embed/object/audio/video, атрибуты-обработчики on*, ссылки javascript: и
data:text, внешние адреса в href/xlink:href и в url() внутри стилей.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

SVG_CONTENT_TYPE = "image/svg+xml"

_FORBIDDEN_TAGS = frozenset({"script", "foreignobject", "iframe", "embed", "object", "audio", "video"})
_HREF_ATTRIBUTES = frozenset({"href", "{http://www.w3.org/1999/xlink}href"})
_DECLARATION = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
_EXTERNAL_URL = re.compile(r"url\(\s*['\"]?\s*(?!#|data:image/)", re.IGNORECASE)


def looks_like_svg(data: bytes) -> bool:
    head = data.lstrip(b"\xef\xbb\xbf \t\r\n")[:4096].lower()
    if head.startswith(b"<svg"):
        return True
    return head.startswith((b"<?xml", b"<!--")) and b"<svg" in head


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def _dangerous_value(value: str) -> bool:
    compact = re.sub(r"\s+", "", value).lower()
    return compact.startswith("javascript:") or compact.startswith("data:text") or compact.startswith("vbscript:")


def svg_is_safe(data: bytes) -> bool:
    if _DECLARATION.search(data):
        return False
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return False
    if _local(root.tag) != "svg":
        return False
    for element in root.iter():
        tag = _local(element.tag) if isinstance(element.tag, str) else ""
        if tag in _FORBIDDEN_TAGS:
            return False
        for name, value in element.attrib.items():
            local = _local(name)
            if local.startswith("on"):
                return False
            if _dangerous_value(value):
                return False
            if name in _HREF_ATTRIBUTES or local == "href":
                stripped = value.strip()
                if stripped and not (stripped.startswith("#") or stripped.lower().startswith("data:image/")):
                    return False
            if local == "style" and _EXTERNAL_URL.search(value):
                return False
        if tag == "style" and element.text and (
            "@import" in element.text.lower() or _EXTERNAL_URL.search(element.text)
        ):
            return False
    return True
