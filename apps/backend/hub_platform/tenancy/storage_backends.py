from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured, SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage

from hub_platform.tenancy.database import current_tenant_id


def _assert_tenant_key(name: str) -> None:
    organization_id = current_tenant_id()
    if organization_id is None:
        raise SuspiciousFileOperation("Tenant storage access requires database context")

    from hub_platform.identity.models import Organization

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


class TenantStorageGuardMixin:
    def open(self, name, mode="rb"):
        _assert_tenant_key(name)
        return super().open(name, mode)

    def save(self, name, content, max_length=None):
        _assert_tenant_key(name)
        return super().save(name, content, max_length=max_length)

    def delete(self, name):
        _assert_tenant_key(name)
        return super().delete(name)

    def exists(self, name):
        _assert_tenant_key(name)
        return super().exists(name)

    def size(self, name):
        _assert_tenant_key(name)
        return super().size(name)

    def url(self, name, *args, **kwargs):
        _assert_tenant_key(name)
        return super().url(name, *args, **kwargs)

    def path(self, name):
        _assert_tenant_key(name)
        return super().path(name)


class TenantFileSystemStorage(TenantStorageGuardMixin, FileSystemStorage):
    pass


def _assert_user_key(name: str) -> None:
    normalized = str(name).replace("\\", "/").lstrip("/")
    if not normalized.startswith("users/"):
        raise SuspiciousFileOperation("User storage key must live under users/")


class UserStorageGuardMixin:
    """Хранилище файлов пользователя (фото профиля): ключи только под users/,
    без тенантного контекста — пользователь общий для организаций."""

    def open(self, name, mode="rb"):
        _assert_user_key(name)
        return super().open(name, mode)

    def save(self, name, content, max_length=None):
        _assert_user_key(name)
        return super().save(name, content, max_length=max_length)

    def delete(self, name):
        _assert_user_key(name)
        return super().delete(name)

    def exists(self, name):
        _assert_user_key(name)
        return super().exists(name)

    def size(self, name):
        _assert_user_key(name)
        return super().size(name)

    def path(self, name):
        _assert_user_key(name)
        return super().path(name)


class UserFileSystemStorage(UserStorageGuardMixin, FileSystemStorage):
    pass


try:
    from storages.backends.s3 import S3Storage
except ImportError:  # pragma: no cover - deployment configuration guard
    S3Storage = None


if S3Storage is not None:

    class TenantS3Storage(TenantStorageGuardMixin, S3Storage):
        pass

    class UserS3Storage(UserStorageGuardMixin, S3Storage):
        pass

else:

    class TenantS3Storage:
        def __init__(self, *args, **kwargs) -> None:
            raise ImproperlyConfigured("django-storages[s3] is required for S3 storage")

    class UserS3Storage(TenantS3Storage):
        pass
