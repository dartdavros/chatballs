"""Перенос локальных файлов в S3 (worker, событие storage.migration_requested).

Копирует всё содержимое MEDIA_ROOT (organizations/… и users/…) в бакет,
пропуская уже существующие ключи; локальные файлы не удаляет — динамический
бэкенд читает из обоих мест, а удалить каталог админ может после проверки.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.utils import timezone

from chatballs.events.handlers import register
from chatballs.i18n import t
from chatballs.tenancy import storage_settings as ss
from chatballs.tenancy.context import TenantContext

logger = logging.getLogger(__name__)

STORAGE_MIGRATION_REQUESTED = "storage.migration_requested"


def _local_keys(root: Path) -> list[str]:
    keys: list[str] = []
    if not root.exists():
        return keys
    for base, _dirs, files in os.walk(root):
        for filename in files:
            full = Path(base) / filename
            keys.append(full.relative_to(root).as_posix())
    return sorted(keys)


def migrate_local_to_s3(row: ss.StorageSettings, *, batch_progress: int = 25) -> int:
    config = ss.config_from_settings(row)
    if not config.s3_configured:
        raise ValueError(t("settings.s3_not_configured"))
    s3 = ss.build_s3_storage(config)
    root = Path(settings.MEDIA_ROOT)
    keys = _local_keys(root)
    row.migration_total = len(keys)
    row.migration_done = 0
    row.save(update_fields=["migration_total", "migration_done", "updated_at"])
    done = 0
    for key in keys:
        if not s3.exists(key):
            with (root / key).open("rb") as source:
                s3.save(key, File(source))
        done += 1
        if done % batch_progress == 0:
            row.migration_done = done
            row.save(update_fields=["migration_done", "updated_at"])
    row.migration_done = done
    return done


@register(STORAGE_MIGRATION_REQUESTED)
def handle_storage_migration_requested(payload: dict, context: TenantContext | None) -> None:
    row = ss.StorageSettings.load()
    try:
        migrate_local_to_s3(row)
    except Exception as error:  # noqa: BLE001 — статус для админа важнее типа ошибки
        logger.exception("Storage migration failed")
        row.migration_status = ss.StorageMigrationStatus.FAILED
        row.migration_error = str(error)[:500]
    else:
        row.migration_status = ss.StorageMigrationStatus.DONE
        row.migration_error = ""
    row.migration_finished_at = timezone.now()
    row.save()
