"""Настройки самой установки: одна строка на инсталляцию, без RLS.

Адрес, по которому открывают установку, продукт узнаёт не из переменной
окружения, а от человека: он поднимает докер на сервере, открывает его по IP
или по своему домену и проходит мастер первого запуска. Адрес из мастера
запоминается здесь, и дальше именно он считается публичным адресом установки —
на нём строятся ссылки и по нему проверяются входящие Host.
"""

from __future__ import annotations

import os
import threading
import time

from django.db import models

from chatballs.identity.crypto import EncryptedCharField
from chatballs.support_portals.addressing import normalize_domain


class InstanceSettings(models.Model):
    SINGLETON_PK = 1

    # Хост без схемы и порта: «crm.example.com» или «203.0.113.10».
    public_host = models.CharField(max_length=253, blank=True, default="")
    # Схема, по которой установку открывают снаружи. Меняется вместе с
    # адресом, когда перед установкой появляется домен и сертификат.
    public_scheme = models.CharField(max_length=5, blank=True, default="")

    # Почта установки: через неё уходят приглашения сотрудникам и сброс
    # пароля. Пока не задана, письма пишутся в лог — приглашать некого.
    email_host = models.CharField(max_length=253, blank=True, default="")
    email_port = models.PositiveIntegerField(default=587)
    email_user = models.CharField(max_length=255, blank=True, default="")
    email_password = EncryptedCharField(max_length=512, blank=True, default="")
    email_use_tls = models.BooleanField(default=True)
    email_from = models.CharField(max_length=255, blank=True, default="")

    # Адреса TURN-серверов для звонков через relay. Секрет сюда не пишется:
    # он общий с coturn и живёт в томе секретов, чтобы не вводить его дважды.
    turn_urls = models.TextField(blank=True, default="")
    turn_ttl_seconds = models.PositiveIntegerField(default=3600)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки установки"

    def __str__(self) -> str:
        return f"instance:{self.public_host or 'не задан'}"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)
        invalidate_cache()

    @classmethod
    def load(cls) -> InstanceSettings:
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj


_CACHE_TTL_SECONDS = 10.0
_lock = threading.Lock()
_cached: tuple[float, str] | None = None


def invalidate_cache() -> None:
    global _cached
    with _lock:
        _cached = None


def public_host() -> str:
    """Адрес установки, запомненный мастером, или пустая строка."""

    global _cached
    now = time.monotonic()
    with _lock:
        if _cached is not None and now - _cached[0] < _CACHE_TTL_SECONDS:
            return _cached[1]
    try:
        row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
        value = row.public_host if row is not None else ""
    except Exception:  # таблицы ещё нет (первые миграции)
        return ""
    with _lock:
        _cached = (now, value)
    return value


def remember_public_host(raw_host: str, scheme: str = "http") -> None:
    """Запомнить адрес, на котором прошли мастер, если он ещё не задан."""

    host = normalize_domain(raw_host.partition(":")[0])
    if not host:
        return
    row = InstanceSettings.load()
    if row.public_host:
        return
    row.public_host = host
    row.public_scheme = "https" if scheme == "https" else "http"
    row.save(update_fields=["public_host", "public_scheme", "updated_at"])


def public_base_url() -> str:
    """Адрес установки для абсолютных ссылок, уходящих наружу.

    Такие ссылки агент отдаёт клиенту в мессенджер, поэтому «localhost»
    здесь недопустим. Источник — адрес, на котором прошли мастер (и который
    владелец может поменять в «Настройках»); переменная окружения остаётся
    переопределением для установок, ведущих конфигурацию сами.
    """

    from django.conf import settings

    configured = os.environ.get("CHATBALLS_PUBLIC_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    try:
        row = InstanceSettings.objects.filter(
            pk=InstanceSettings.SINGLETON_PK
        ).first()
    except Exception:
        row = None
    if row is not None and row.public_host:
        scheme = row.public_scheme or "http"
        return f"{scheme}://{row.public_host}"
    return str(settings.CHATBALLS_PUBLIC_BASE_URL).rstrip("/")


def email_is_configured() -> bool:
    row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
    return bool(row and row.email_host)


def email_connection():
    """Соединение с почтовым сервером из настроек установки.

    Пока владелец не задал SMTP, возвращается None — письма уходят в бэкенд по
    умолчанию (в коробке это консоль), и в «Настройках» видно, что почта не
    настроена.
    """

    from django.core.mail import get_connection

    row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
    if row is None or not row.email_host:
        return None
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=row.email_host,
        port=row.email_port,
        username=row.email_user or None,
        password=row.email_password or None,
        use_tls=row.email_use_tls,
    )


def email_from_address() -> str:
    """Адрес отправителя: из настроек установки, иначе — общий дефолт."""

    from django.conf import settings

    row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
    if row is not None and row.email_from:
        return row.email_from
    return str(settings.DEFAULT_FROM_EMAIL)


def turn_config() -> tuple[list[str], int]:
    """Адреса TURN и время жизни credentials из настроек установки.

    Пустой список означает «relay не настроен»: звонки идут напрямую и через
    STUN. Переменная окружения, если задана, побеждает.
    """

    from django.conf import settings

    if settings.CHATBALLS_CALL_TURN_URLS:
        return list(settings.CHATBALLS_CALL_TURN_URLS), settings.CHATBALLS_CALL_TURN_TTL_SECONDS
    try:
        row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
    except Exception:
        # Нет БД (юнит-тест без базы, ранние миграции) — берём то, что в
        # настройках процесса.
        return [], settings.CHATBALLS_CALL_TURN_TTL_SECONDS
    if row is None or not row.turn_urls.strip():
        return [], settings.CHATBALLS_CALL_TURN_TTL_SECONDS
    urls = [line.strip() for line in row.turn_urls.splitlines() if line.strip()]
    return urls, row.turn_ttl_seconds or settings.CHATBALLS_CALL_TURN_TTL_SECONDS
