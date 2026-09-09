"""Настройки хранилища файлов инстанса (вложения знаний, голосовые, фото, логотипы).

По умолчанию файлы лежат локально (MEDIA_ROOT, bind-mount data/media). Админ в
«Настройках» может переключить инстанс на внешнее S3-совместимое хранилище —
без правок .env и перезапуска: бэкенды читают настройки из БД с коротким
кэшем. Секреты S3 шифруются (Fernet) как и остальные секреты системы.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from chatballs.i18n import t
from chatballs.identity.crypto import EncryptedCharField


class StorageBackend(models.TextChoices):
    LOCAL = "LOCAL", "Локальный диск"
    S3 = "S3", "S3-совместимое хранилище"


class StorageMigrationStatus(models.TextChoices):
    IDLE = "IDLE", "Не запускался"
    RUNNING = "RUNNING", "Идёт"
    DONE = "DONE", "Завершён"
    FAILED = "FAILED", "Ошибка"


class StorageSettings(models.Model):
    """Единственная строка (pk=1): где инстанс хранит файлы."""

    SINGLETON_PK = 1

    backend = models.CharField(max_length=8, choices=StorageBackend.choices, default=StorageBackend.LOCAL)
    s3_bucket = models.CharField(max_length=255, blank=True, default="")
    s3_endpoint_url = models.URLField(max_length=512, blank=True, default="")
    s3_region = models.CharField(max_length=64, blank=True, default="")
    s3_access_key = EncryptedCharField(max_length=512, blank=True, default="")
    s3_secret_key = EncryptedCharField(max_length=512, blank=True, default="")
    s3_addressing_style = models.CharField(max_length=8, default="path")
    s3_verified_at = models.DateTimeField(null=True, blank=True)
    s3_last_error = models.CharField(max_length=500, blank=True, default="")
    migration_status = models.CharField(
        max_length=8, choices=StorageMigrationStatus.choices, default=StorageMigrationStatus.IDLE
    )
    migration_total = models.PositiveIntegerField(default=0)
    migration_done = models.PositiveIntegerField(default=0)
    migration_error = models.CharField(max_length=500, blank=True, default="")
    migration_started_at = models.DateTimeField(null=True, blank=True)
    migration_finished_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        "identity.HumanUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки хранилища"

    def __str__(self) -> str:
        return f"storage-settings:{self.backend.lower()}"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)
        invalidate_cache()

    @classmethod
    def load(cls) -> StorageSettings:
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj

    @property
    def s3_configured(self) -> bool:
        return bool(self.s3_bucket and self.s3_access_key and self.s3_secret_key)


@dataclass(frozen=True)
class StorageConfig:
    backend: str
    bucket: str = ""
    endpoint_url: str = ""
    region: str = ""
    access_key: str = ""
    secret_key: str = ""
    addressing_style: str = "path"

    @property
    def s3_configured(self) -> bool:
        return bool(self.bucket and self.access_key and self.secret_key)

    @property
    def is_s3(self) -> bool:
        return self.backend == StorageBackend.S3 and self.s3_configured


LOCAL_CONFIG = StorageConfig(backend=StorageBackend.LOCAL)

# Кэш конфигурации на процесс: web и worker перечитывают строку раз в несколько
# секунд; save() сбрасывает кэш в своём процессе сразу.
_CACHE_TTL_SECONDS = 10.0
_lock = threading.Lock()
_cached: tuple[float, StorageConfig] | None = None


def invalidate_cache() -> None:
    global _cached
    with _lock:
        _cached = None


def current_config() -> StorageConfig:
    global _cached
    now = time.monotonic()
    with _lock:
        if _cached is not None and now - _cached[0] < _CACHE_TTL_SECONDS:
            return _cached[1]
    config = _load_config()
    with _lock:
        _cached = (now, config)
    return config


def _load_config() -> StorageConfig:
    try:
        row = StorageSettings.objects.filter(pk=StorageSettings.SINGLETON_PK).first()
    except Exception:  # таблицы ещё нет (первые миграции) — локальный диск
        return LOCAL_CONFIG
    if row is None:
        return LOCAL_CONFIG
    # Реквизиты S3 сохраняются и при локальном режиме: файлы, оставшиеся в бакете
    # после переключения назад, продолжают читаться.
    return config_from_settings(row)


def config_from_settings(row: StorageSettings) -> StorageConfig:
    return StorageConfig(
        backend=row.backend,
        bucket=row.s3_bucket,
        endpoint_url=row.s3_endpoint_url,
        region=row.s3_region,
        access_key=row.s3_access_key,
        secret_key=row.s3_secret_key,
        addressing_style=row.s3_addressing_style or "path",
    )


def build_s3_storage(config: StorageConfig, *, probe: bool = False):
    """Экземпляр django-storages S3 по конфигурации (без тенантного ограждения —
    его добавляет обёртка). Для проверки — короткие таймауты и без повторов,
    чтобы админ получил ответ за секунды, а не через минуту ретраев boto."""
    try:
        from botocore.config import Config
        from storages.backends.s3 import S3Storage
    except ImportError as error:  # pragma: no cover - deployment guard
        raise ValidationError(t("settings.storages_missing")) from error
    client_config = (
        Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1})
        if probe
        else Config(connect_timeout=10, read_timeout=60, retries={"max_attempts": 3})
    )
    return S3Storage(
        client_config=client_config,
        bucket_name=config.bucket,
        endpoint_url=config.endpoint_url or None,
        region_name=config.region or None,
        access_key=config.access_key or None,
        secret_key=config.secret_key or None,
        addressing_style=config.addressing_style or "path",
        default_acl=None,
        file_overwrite=False,
        querystring_auth=True,
        querystring_expire=900,
    )


def validate_s3_fields(*, bucket: str, endpoint_url: str, region: str, access_key: str, secret_key: str, addressing_style: str) -> None:
    errors: dict[str, str] = {}
    if not bucket.strip():
        errors["s3Bucket"] = "Укажите имя бакета"
    if endpoint_url and not endpoint_url.startswith(("http://", "https://")):
        errors["s3EndpointUrl"] = "Адрес должен начинаться с http:// или https://"
    if not access_key:
        errors["s3AccessKey"] = "Укажите Access Key"
    if not secret_key:
        errors["s3SecretKey"] = "Укажите Secret Key"
    if addressing_style not in {"path", "virtual"}:
        errors["s3AddressingStyle"] = "path или virtual"
    if errors:
        raise ValidationError(errors)


def probe_s3(config: StorageConfig) -> None:
    """Проверка доступа: записать и удалить пробный объект. Бросает ValidationError с текстом."""
    from django.core.files.base import ContentFile

    key = f"chatballs-probe/{uuid.uuid4()}.txt"
    try:
        storage = build_s3_storage(config, probe=True)
        stored = storage.save(key, ContentFile(b"chatballs storage probe"))
        if not storage.exists(stored):
            raise ValidationError({"s3Bucket": "Объект записан, но не читается — проверьте права на чтение"})
        storage.delete(stored)
    except ValidationError:
        raise
    except Exception as error:  # boto/botocore ошибки разнообразны — показываем текст
        raise ValidationError({"s3Bucket": f"Хранилище недоступно: {_short(error)}"}) from error


def _short(error: Exception) -> str:
    text = str(error).strip() or error.__class__.__name__
    return text[:300]


def mark_verified(row: StorageSettings, *, error: str = "") -> None:
    row.s3_verified_at = None if error else timezone.now()
    row.s3_last_error = error[:500]
    row.save(update_fields=["s3_verified_at", "s3_last_error", "updated_at"])
