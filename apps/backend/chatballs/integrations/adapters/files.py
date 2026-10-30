"""Сохранение больших/бинарных данных операции в штатное хранилище (SPEC-0037 R-4).

Квота организации резервируется до записи и закрывается фактическим
размером, как у остальных файлов приложения (``webchat/assets.py``). Наружу
отдаётся только ссылка: содержимое не попадает в JSON запуска, логи и outbox.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import IO

from django.core.files.base import File
from django.db import transaction

from chatballs.integrations.adapters.contracts import FileRef
from chatballs.integrations.adapters.transport import StoreFile
from chatballs.integrations.models import Integration, ServiceFile
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.storage import adjust_storage_usage
from chatballs.tenancy.storage_quota import finalize_storage, release_storage, reserve_storage

_HASH_CHUNK = 64 * 1024


def file_store(*, context: TenantContext, integration: Integration) -> StoreFile:
    def store(name: str, content_type: str, stream: IO[bytes], size: int) -> FileRef:
        return store_service_file(
            context=context, integration=integration, name=name, content_type=content_type, stream=stream, size=size
        )

    return store


def store_service_file(
    *, context: TenantContext, integration: Integration, name: str, content_type: str, stream: IO[bytes], size: int
) -> FileRef:
    # Ответ внешнего сервиса уже получен в spool. Persistence должна сама
    # установить tenant: сетевые обработчики работают вне tenant-транзакции.
    with tenant_atomic(context):
        return _store_service_file(context=context, integration=integration, name=name,
                                   content_type=content_type, stream=stream, size=size)


def _store_service_file(
    *, context: TenantContext, integration: Integration, name: str, content_type: str, stream: IO[bytes], size: int
) -> FileRef:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(_HASH_CHUNK), b""):
        digest.update(chunk)
    stream.seek(0)
    record = ServiceFile(
        organization_id=context.organization_id,
        integration=integration,
        name=name[:255],
        content_type=content_type[:128],
        size=size,
        sha256=digest.hexdigest(),
    )
    reservation_key = f"service-file:{uuid.uuid4()}"
    reserve_storage(context=context, expected_bytes=size, idempotency_key=reservation_key)
    try:
        record.file.save(name, File(stream), save=False)
        with transaction.atomic():
            record.save()
        finalize_storage(context=context, idempotency_key=reservation_key, actual_bytes=size)
    except Exception:
        if record.file.name:
            record.file.delete(save=False)
        release_storage(context=context, idempotency_key=reservation_key)
        raise
    return FileRef(file_id=str(record.public_id), name=record.name, content_type=record.content_type, size=size)


def discard_service_files(*, context: TenantContext, integration: Integration) -> None:
    """Перед удалением подключения: место освобождается сразу, файлы — после коммита."""

    files = list(integration.service_files.values_list("file", "size"))
    if not files:
        return
    adjust_storage_usage(context=context, delta_bytes=-sum(size for _name, size in files))
    storage = ServiceFile._meta.get_field("file").storage
    organization_id = context.organization_id

    def delete_files() -> None:
        # Ограждение хранилища требует контекст организации.
        with tenant_atomic(organization_id):
            for name, _size in files:
                storage.delete(name)

    transaction.on_commit(delete_files)
