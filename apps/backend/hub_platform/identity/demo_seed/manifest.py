"""Чтение и валидация демонстрационных манифестов из каталога ``data``.

Манифесты — обычный JSON в каталоге ``demo_seed/data/``, отдельный файл на домен.
Редактируются вручную; версия схемы проверяется при загрузке. Медиа-вложения
(логотип, файлы знаний) лежат в ``demo_seed/data/media/``.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

DATA_DIR = Path(__file__).resolve().parent / "data"
MEDIA_DIR = DATA_DIR / "media"

SCHEMA_VERSION = 1

#: Файлы манифестов по доменам (имя файла без расширения).
MANIFEST_FILES: tuple[str, ...] = (
    "organization",
    "catalog",
    "channels_ai",
    "conversations",
    "commerce",
    "support",
    "operations",
)


class ManifestError(ImproperlyConfigured):
    """Нарушение схемы или целостности манифеста демо-данных."""


@cache
def load(name: str) -> dict | list:
    """Возвращает разобранный JSON-манифест ``name`` с проверкой схемы.

    Кэшируется на процесс: повторные вызовы во время одного прогона сида
    не перечитывают файл.
    """
    path = DATA_DIR / f"{name}.json"
    if not path.is_file():
        raise ManifestError(f"Demo manifest not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ManifestError(f"Demo manifest {path} is not valid JSON: {error}") from error
    if name == "organization":
        _validate_organization(payload)
    else:
        _validate_section(payload, name)
    return payload


def media_path(filename: str) -> Path:
    """Абсолютный путь к файлу-вложению из каталога ``data/media``."""
    path = MEDIA_DIR / filename
    if not path.is_file():
        raise ManifestError(f"Demo media file not found: {path}")
    return path


def media_text(filename: str) -> str:
    """Текстовое содержимое вложения (для SVG/Markdown)."""
    return media_path(filename).read_text(encoding="utf-8")


def _validate_organization(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ManifestError("organization manifest must be a JSON object")
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ManifestError(f"organization manifest schemaVersion must be {SCHEMA_VERSION}")
    org = payload.get("organization")
    if not isinstance(org, dict):
        raise ManifestError("organization block is required")
    for key in ("slug", "name", "timezone", "currency"):
        if not org.get(key):
            raise ManifestError(f"organization.{key} is required")


def _validate_section(payload: dict | list, name: str) -> None:
    if not isinstance(payload, dict) or payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ManifestError(f"{name} manifest schemaVersion must be {SCHEMA_VERSION}")
