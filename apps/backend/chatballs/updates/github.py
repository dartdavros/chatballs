"""Канал релизов: страница релизов GitHub.

Установка спрашивает у GitHub последний релиз репозитория продукта и берёт
из него версию, заметки и ссылку на compose.yaml. Никаких токенов: релизы
публичные, лимита анонимных запросов хватает при проверке раз в несколько
часов.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from django.conf import settings

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+)?$")
_TIMEOUT_SECONDS = 15


@dataclass(frozen=True, slots=True)
class Release:
    version: str
    name: str
    notes: str
    published_at: datetime | None
    compose_url: str
    page_url: str


class ReleaseChannelError(Exception):
    """Канал релизов недоступен или ответил не тем, что ожидалось."""


def parse_version(tag: str) -> str | None:
    version = tag.strip()
    if version.startswith(("v", "V")):
        version = version[1:]
    return version if VERSION_RE.match(version) else None


def version_key(version: str) -> tuple:
    """Ключ сравнения: числовая тройка, затем метка (без метки — новее)."""

    core, _, label = version.partition("-")
    core = core.split(".")[:3]
    numbers = tuple(int(part) for part in core if part.isdigit())
    return (numbers, label == "", label)


def is_newer(candidate: str, current: str) -> bool:
    if not VERSION_RE.match(candidate) or not VERSION_RE.match(current or ""):
        # Dev-сборка без версии: обновлять нечего и не с чем сравнивать.
        return False
    return version_key(candidate) > version_key(current)


def expected_compose_url(version: str) -> str:
    return f"https://github.com/{settings.CHATBALLS_UPDATE_REPO}/releases/download/v{version}/compose.yaml"


def fetch_latest_release() -> Release:
    url = f"https://api.github.com/repos/{settings.CHATBALLS_UPDATE_REPO}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"chatballs/{settings.CHATBALLS_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise ReleaseChannelError(str(error)) from error
    version = parse_version(str(payload.get("tag_name", "")))
    if version is None:
        raise ReleaseChannelError(f"unexpected tag {payload.get('tag_name')!r}")
    compose_url = next(
        (
            str(asset.get("browser_download_url", ""))
            for asset in payload.get("assets", [])
            if asset.get("name") == "compose.yaml"
        ),
        "",
    )
    if compose_url != expected_compose_url(version):
        raise ReleaseChannelError("release has no compose.yaml at the expected address")
    published = None
    raw_published = str(payload.get("published_at", "")).strip()
    if raw_published:
        try:
            published = datetime.fromisoformat(raw_published.replace("Z", "+00:00"))
        except ValueError:
            published = None
    return Release(
        version=version,
        name=str(payload.get("name") or f"v{version}"),
        notes=str(payload.get("body") or ""),
        published_at=published,
        compose_url=compose_url,
        page_url=str(payload.get("html_url") or ""),
    )
