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

    # Хост без схемы и порта: «crm.example.com» или «203.0.113.10». Именно
    # хост, а не адрес: по нему проверяются входящие Host, строятся домены
    # порталов и адреса TURN — порт им чужой.
    public_host = models.CharField(max_length=253, blank=True, default="")
    # Порт, если установку открывают не на стандартном для схемы: шлюз
    # опубликован как 8081, а 80-й занят панелью или другим сервисом. Пусто —
    # порт схемы (80/443), и в ссылках его нет.
    public_port = models.PositiveIntegerField(null=True, blank=True)
    # Предыдущий адрес: остаётся принятым, чтобы смена адреса не выбрасывала
    # того, кто её делает. Владелец меняет адрес заранее — до того, как домен
    # начал резолвиться и получил сертификат, — и сидит при этом на старом.
    # Без этого он получал «Invalid host» через десять секунд после
    # сохранения, а мастер уже закрыт: вернуться было бы неоткуда.
    previous_public_host = models.CharField(max_length=253, blank=True, default="")
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

    # Язык установки: на нём открываются экраны, где организации ещё нет, —
    # логин, сброс пароля, мастер первого запуска, — и он же служит умолчанием
    # для организаций, которые своего языка не выбрали.
    default_language = models.CharField(max_length=5, blank=True, default="ru")

    # Адреса TURN-серверов для звонков через relay. Секрет сюда не пишется:
    # он общий с coturn и живёт в томе секретов, чтобы не вводить его дважды.
    turn_urls = models.TextField(blank=True, default="")
    turn_ttl_seconds = models.PositiveIntegerField(default=3600)

    # Частные адреса для инструментов агентов (SPEC-0023 R-17): настройка
    # касается агентов всех организаций, поэтому хранится, кто и когда её
    # включил. При выключении оба поля очищаются — история остаётся в журнале
    # аудита.
    tools_private_network = models.BooleanField(default=False)
    tools_private_network_enabled_by = models.ForeignKey(
        "identity.HumanUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    tools_private_network_enabled_at = models.DateTimeField(null=True, blank=True)
    external_checks_enabled = models.BooleanField(default=True)
    external_checks_revision = models.PositiveBigIntegerField(default=0)
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


def external_checks_allowed() -> bool:
    enabled = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).values_list(
        "external_checks_enabled", flat=True
    ).first()
    return enabled is not False


_CACHE_TTL_SECONDS = 10.0
# Перечитать кэш при промахе по хосту можно не чаще раза в секунду на процесс:
# иначе поток запросов с чужим Host превращался бы в поток запросов к базе.
_MISS_REFRESH_SECONDS = 1.0
_lock = threading.Lock()
_cached: tuple[float, tuple[str, str]] | None = None
_last_miss_refresh = 0.0


def invalidate_cache() -> None:
    global _cached
    with _lock:
        _cached = None


def _hosts() -> tuple[str, str]:
    """Текущий и предыдущий адрес установки (оба могут быть пустыми)."""

    global _cached
    now = time.monotonic()
    with _lock:
        if _cached is not None and now - _cached[0] < _CACHE_TTL_SECONDS:
            return _cached[1]
    try:
        row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
        value = (row.public_host, row.previous_public_host) if row is not None else ("", "")
    except Exception:  # таблицы ещё нет (первые миграции)
        return ("", "")
    with _lock:
        _cached = (now, value)
    return value


def public_host() -> str:
    """Адрес установки, запомненный мастером, или пустая строка."""

    return _hosts()[0]


def accepted_hosts() -> tuple[str, ...]:
    """Адреса, которые установка признаёт своими: текущий и предыдущий."""

    return tuple(host for host in _hosts() if host)


def host_is_accepted(host: str) -> bool:
    """Свой ли это адрес — с перечитыванием кэша при промахе.

    Кэш живёт в каждом процессе gunicorn отдельно. Мастер первого запуска или
    смена адреса в «Настройках» сбрасывают его только там, где выполнялись;
    соседний процесс до 10 секунд отвечал бы «Invalid host» на адрес, который
    установка уже считает своим. Поэтому промах — повод перечитать строку, но
    не чаще раза в секунду.
    """

    global _last_miss_refresh
    if not host:
        return False
    known = {normalize_domain(item) for item in accepted_hosts()}
    if host in known:
        return True
    now = time.monotonic()
    with _lock:
        if now - _last_miss_refresh < _MISS_REFRESH_SECONDS:
            return False
        _last_miss_refresh = now
    invalidate_cache()
    return host in {normalize_domain(item) for item in accepted_hosts()}


def default_language() -> str:
    """Язык установки: экраны до входа и умолчание для организаций.

    Читается без кэша, в отличие от адреса. Кэш с TTL здесь означал бы, что
    один и тот же запрос стоит то одного запроса к базе, то нуля — в зависимости
    от того, попал ли он в окно, — и язык установки некоторое время оставался бы
    старым в тех процессах, которые смены не видели. Цена честности — один
    поиск singleton-строки по первичному ключу, и только у запросов, которые
    вообще досюда дошли: у сотрудника со своим языком и у организации со своим
    до этой ветки дело не доходит.

    Пустая строка означает установку, где язык ещё ни разу не задавали, — и
    приводит к языку по умолчанию из ``chatballs.i18n``.
    """

    from chatballs.i18n.languages import normalize_language

    try:
        row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
    except Exception:  # таблицы ещё нет (первые миграции)
        return ""
    return normalize_language(row.default_language) if row is not None else ""


def tools_private_network_allowed() -> bool:
    """Разрешены ли инструментам агентов адреса локальной сети.

    Без кэша, как и язык: выключенная настройка должна закрыть частные адреса
    сразу во всех процессах, а не через TTL.
    """

    try:
        row = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).first()
    except Exception:  # таблицы ещё нет (первые миграции)
        return False
    return bool(row and row.tools_private_network)


def remember_default_language(language: str) -> None:
    """Записать язык установки. Пустое значение ничего не меняет."""

    from chatballs.i18n.languages import normalize_language

    code = normalize_language(language)
    if not code:
        return
    row = InstanceSettings.load()
    if row.default_language != code:
        row.default_language = code
        row.save(update_fields=["default_language", "updated_at"])


_DEFAULT_PORTS = {"http": 80, "https": 443}


def split_address(raw: str, scheme: str) -> tuple[str, int | None] | None:
    """Хост и порт из «host[:port]»; None — адрес не разобрать.

    Порт схемы (80 у http, 443 у https) отбрасывается: в ссылке он лишний, а
    хранить его значило бы различать два одинаковых адреса.
    """

    host, separator, port_text = raw.strip().rpartition(":")
    if not separator:
        return normalize_domain(port_text), None
    host = normalize_domain(host)
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        return None
    port = int(port_text)
    return host, None if port == _DEFAULT_PORTS.get(scheme) else port


def format_address(host: str, port: int | None) -> str:
    """Адрес для ссылок и для поля в «Настройках»: хост и порт, если он не схемы."""

    return f"{host}:{port}" if host and port else host


def remember_public_host(raw_host: str, scheme: str = "http") -> None:
    """Запомнить адрес, на котором прошли мастер, если он ещё не задан.

    Порт запоминается вместе с хостом: установку, открытую на ``ip:8081``,
    дальше открывают там же, и ссылки без порта вели бы в пустоту.
    """

    scheme = "https" if scheme == "https" else "http"
    parsed = split_address(raw_host, scheme)
    if parsed is None or not parsed[0]:
        return
    row = InstanceSettings.load()
    if row.public_host:
        return
    row.public_host, row.public_port = parsed
    row.public_scheme = scheme
    row.save(update_fields=["public_host", "public_port", "public_scheme", "updated_at"])


def configured_public_base_url() -> str:
    """Актуальный настроенный адрес установки без встроенного значения."""
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
        return f"{scheme}://{format_address(row.public_host, row.public_port)}"
    return ""


def public_base_url() -> str:
    """Адрес установки для абсолютных ссылок, уходящих наружу."""
    from django.conf import settings

    return configured_public_base_url() or str(settings.CHATBALLS_PUBLIC_BASE_URL).rstrip("/")


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


# Порт relay в коробке: на нём coturn слушает и TURN, и STUN (compose.yaml).
TURN_PORT = 3478


def default_turn_urls(host: str = "") -> list[str]:
    """Адреса relay, которые работают в коробке без единой настройки.

    Relay стоит на том же сервере и на том же адресе, что и сама установка, —
    адрес известен с мастера первого запуска, и заставлять человека вписывать
    его руками незачем. UDP идёт первым, TCP — запасным для сетей, где UDP
    режут.
    """
    host = host or public_host()
    if not host:
        return []
    return [
        f"turn:{host}:{TURN_PORT}?transport=udp",
        f"turn:{host}:{TURN_PORT}?transport=tcp",
    ]


def default_stun_urls(host: str = "") -> list[str]:
    """STUN отдаёт тот же coturn на том же порту."""
    host = host or public_host()
    return [f"stun:{host}:{TURN_PORT}"] if host else []


def turn_config() -> tuple[list[str], int]:
    """Адреса TURN и время жизни credentials.

    Порядок: переменная окружения (если её всё-таки задали), затем то, что
    владелец вписал в «Настройки», затем адреса коробки по адресу установки.
    Пустой список остаётся только там, где адрес установки ещё не известен.
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
        return default_turn_urls(), settings.CHATBALLS_CALL_TURN_TTL_SECONDS
    urls = [line.strip() for line in row.turn_urls.splitlines() if line.strip()]
    return urls, row.turn_ttl_seconds or settings.CHATBALLS_CALL_TURN_TTL_SECONDS
