"""Адрес, на который владелец направляет A-запись домена портала.

Раньше это была переменная окружения с обязательной проверкой при старте, а у
коробки её задавать негде — поэтому значение по умолчанию схлопывалось в
``127.0.0.1``, и продукт печатал владельцу инструкцию «направьте домен на
loopback». Теперь источник тот же, что и у всего остального адресного: адрес
самой установки, который человек ввёл в мастере первого запуска и меняет в
«Настройках».

Порядок: явная переменная окружения (контуры, которые ведут конфигурацию
сами) → адрес установки, если это IPv4 → его A-запись, если это домен. Пусто
— значит показывать нечего: до мастера адреса ещё нет.
"""

from __future__ import annotations

import threading
import time
from ipaddress import IPv4Address

from django.conf import settings

_CACHE_TTL_SECONDS = 60.0
_lock = threading.Lock()
_cached: tuple[float, str] | None = None


def invalidate_cache() -> None:
    global _cached
    with _lock:
        _cached = None


def _as_ipv4(value: str) -> str:
    try:
        return str(IPv4Address(value.strip()))
    except ValueError:
        return ""


def _resolve_a_record(hostname: str) -> str:
    import dns.exception
    import dns.resolver

    try:
        answers = dns.resolver.resolve(hostname, "A")
    except (
        dns.resolver.NoAnswer,
        dns.resolver.NXDOMAIN,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ):
        return ""
    for answer in answers:
        address = _as_ipv4(getattr(answer, "address", str(answer).rstrip(".")))
        if address:
            return address
    return ""


def help_public_ipv4() -> str:
    """IPv4 установки для инструкции «направьте A-запись сюда»; пусто — нечего показать."""

    configured = str(getattr(settings, "CHATBALLS_HELP_PUBLIC_IPV4", "") or "")
    if configured:
        return configured

    global _cached
    now = time.monotonic()
    with _lock:
        if _cached is not None and now - _cached[0] < _CACHE_TTL_SECONDS:
            return _cached[1]

    from chatballs.identity.instance_settings import public_host

    try:
        host = public_host()
    except Exception:  # таблицы ещё нет (ранние миграции)
        return ""
    address = _as_ipv4(host) or (_resolve_a_record(host) if host else "")

    with _lock:
        _cached = (now, address)
    return address
