"""Хранилища файлов инстанса.

Куда писать (локальный диск или внешнее S3) решают настройки в БД
(``tenancy.storage_settings``), которые админ меняет в «Настройках» — без .env.
Динамический бэкенд делегирует операции текущему хранилищу; чтение и удаление
при включённом S3 дополнительно смотрят локальный диск, чтобы файлы, загруженные
до переключения, оставались доступны до завершения переноса.

Ограждения ключей остались прежними: тенантные файлы — только под
``organizations/<public_id>/`` своей организации, пользовательские — под ``users/``.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible

from chatballs.tenancy.database import current_tenant_id


def _assert_tenant_key(name: str) -> None:
    organization_id = current_tenant_id()
    if organization_id is None:
        raise SuspiciousFileOperation("Tenant storage access requires database context")

    from chatballs.identity.models import Organization

    try:
        public_id = Organization.objects.values_list("public_id", flat=True).get(
            pk=organization_id
        )
    except Organization.DoesNotExist as error:
        raise SuspiciousFileOperation("Tenant storage organization does not exist") from error
    normalized = str(name).replace("\\", "/").lstrip("/")
    prefix = f"organizations/{public_id}/"
    if not normalized.startswith(prefix):
        raise SuspiciousFileOperation("Storage key belongs to another organization")


def _assert_user_key(name: str) -> None:
    normalized = str(name).replace("\\", "/").lstrip("/")
    if not normalized.startswith("users/"):
        raise SuspiciousFileOperation("User storage key must live under users/")


def local_storage() -> FileSystemStorage:
    return FileSystemStorage(location=settings.MEDIA_ROOT)


class _DynamicStorage(Storage):
    """Делегирует операции текущему бэкенду из настроек инстанса."""

    _s3_cache: tuple[object, object] | None = None

    def _guard(self, name: str) -> None:  # переопределяется наследниками
        raise NotImplementedError

    def _s3(self, config):
        from chatballs.tenancy import storage_settings

        cached = type(self)._s3_cache
        if cached is not None and cached[0] == config:
            return cached[1]
        backend = storage_settings.build_s3_storage(config)
        type(self)._s3_cache = (config, backend)
        return backend

    def _active(self):
        from chatballs.tenancy import storage_settings

        config = storage_settings.current_config()
        return self._s3(config) if config.is_s3 else local_storage()

    def _secondary(self):
        """Второе хранилище, где могут лежать файлы (до/после переноса), или None."""
        from chatballs.tenancy import storage_settings

        config = storage_settings.current_config()
        if config.is_s3:
            return local_storage()
        if config.s3_configured:
            return self._s3(config)
        return None

    def _reader_for(self, name: str):
        """Хранилище, где файл реально лежит: активное, иначе второе."""
        active = self._active()
        if active.exists(name):
            return active
        secondary = self._secondary()
        if secondary is not None and secondary.exists(name):
            return secondary
        return active

    # --- Storage API ---------------------------------------------------------
    def _open(self, name, mode="rb"):
        return self._reader_for(name).open(name, mode)

    def _save(self, name, content):
        return self._active().save(name, content)

    def open(self, name, mode="rb"):
        self._guard(name)
        return self._open(name, mode)

    def save(self, name, content, max_length=None):
        self._guard(name)
        return self._active().save(name, content, max_length=max_length)

    def delete(self, name):
        self._guard(name)
        for storage in (self._active(), self._secondary()):
            if storage is not None and storage.exists(name):
                storage.delete(name)

    def exists(self, name):
        self._guard(name)
        if self._active().exists(name):
            return True
        secondary = self._secondary()
        return secondary is not None and secondary.exists(name)

    def size(self, name):
        self._guard(name)
        return self._reader_for(name).size(name)

    def url(self, name):
        self._guard(name)
        return self._reader_for(name).url(name)

    def path(self, name):
        self._guard(name)
        return self._reader_for(name).path(name)

    def get_available_name(self, name, max_length=None):
        return self._active().get_available_name(name, max_length=max_length)

    def listdir(self, path):
        return self._active().listdir(path)

    def get_accessed_time(self, name):
        return self._reader_for(name).get_accessed_time(name)

    def get_created_time(self, name):
        return self._reader_for(name).get_created_time(name)

    def get_modified_time(self, name):
        return self._reader_for(name).get_modified_time(name)


@deconstructible
class DynamicTenantStorage(_DynamicStorage):
    def _guard(self, name: str) -> None:
        _assert_tenant_key(name)


@deconstructible
class DynamicUserStorage(_DynamicStorage):
    _s3_cache = None

    def _guard(self, name: str) -> None:
        _assert_user_key(name)


# Обратная совместимость имён (миграции/настройки старых установок).
TenantFileSystemStorage = DynamicTenantStorage
UserFileSystemStorage = DynamicUserStorage
TenantS3Storage = DynamicTenantStorage
UserS3Storage = DynamicUserStorage
