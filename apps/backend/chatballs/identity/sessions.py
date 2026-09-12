"""Серверные сессии пользователя: счётчик, список для «Профиля» и отзыв.

Карточка «Активные сессии» (дизайн-базлайн v2, кадр P1) показывает устройство,
адрес и когда сессия была активна. Отдельной таблицы нет: браузер и адрес
пишутся в саму сессию при входе, отметка активности обновляется middleware
не чаще раза в минуту.
"""

from __future__ import annotations

import re

from django.contrib.sessions.models import Session
from django.utils import timezone

from chatballs.i18n import t

SESSION_AGENT_KEY = "device_agent"
SESSION_IP_KEY = "device_ip"
SESSION_STARTED_KEY = "device_started"
SESSION_SEEN_KEY = "device_seen"
# Чаще раза в минуту отметку не обновляем: иначе запись сессии на каждый запрос.
SEEN_THROTTLE_SECONDS = 60

_BROWSERS = (
    ("YaBrowser", "Яндекс.Браузер"),
    ("Edg/", "Edge"),
    ("OPR/", "Opera"),
    ("Firefox", "Firefox"),
    ("Chrome", "Chrome"),
    ("Safari", "Safari"),
)
_PLATFORMS = (
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Macintosh", "macOS"),
    ("Windows", "Windows"),
    ("Linux", "Linux"),
)


def describe_agent(user_agent: str) -> str:
    """«Chrome · macOS» из строки User-Agent; неизвестное — «Браузер»."""
    browser = next((label for token, label in _BROWSERS if token in user_agent), "")
    platform = next((label for token, label in _PLATFORMS if token in user_agent), "")
    if browser and platform:
        return f"{browser} · {platform}"
    return browser or platform or t("identity.browser_unknown")


def device_kind(user_agent: str) -> str:
    """Какой значок ставить в строке сессии: телефон, ноутбук или монитор."""
    if any(token in user_agent for token in ("iPhone", "Android", "iPad")):
        return "phone"
    if "Macintosh" in user_agent:
        return "laptop"
    return "monitor"


def mask_ip(value: str) -> str:
    """Адрес показываем частично: «91.108.•.•» (кадр P1)."""
    if not value:
        return ""
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", value):
        first, second, *_ = value.split(".")
        return f"{first}.{second}.•.•"
    head = value.split(":")[0]
    return f"{head}:•" if head else ""


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def remember_device(request) -> None:
    """Запомнить браузер и адрес в сессии — вызывается сразу после login()."""
    now = timezone.now().isoformat()
    request.session[SESSION_AGENT_KEY] = request.META.get("HTTP_USER_AGENT", "")[:400]
    request.session[SESSION_IP_KEY] = client_ip(request)
    request.session[SESSION_STARTED_KEY] = now
    request.session[SESSION_SEEN_KEY] = now


def touch_session(request) -> None:
    """Обновить отметку активности, но не чаще SEEN_THROTTLE_SECONDS."""
    previous = request.session.get(SESSION_SEEN_KEY)
    now = timezone.now()
    if previous:
        try:
            elapsed = (now - timezone.datetime.fromisoformat(previous)).total_seconds()
        except (TypeError, ValueError):
            elapsed = SEEN_THROTTLE_SECONDS
        if elapsed < SEEN_THROTTLE_SECONDS:
            return
    request.session[SESSION_SEEN_KEY] = now.isoformat()


def _decoded_sessions(user_id: int):
    """Живые сессии пользователя.

    Владельца сессии хранит её подписанное содержимое, отдельной колонки у
    django_session нет — приходится расшифровывать строки и сравнивать. Отбор
    по expire_date держит перебор в размере одновременно открытых сессий:
    просроченные строки Django сам не удаляет, и без фильтра стоимость
    просмотра карточки сотрудника росла бы вместе с историей входов за всё
    время (чистит их maintenance-цикл воркера, clearsessions).
    """
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(user_id):
            yield session, data


def count_user_sessions(user_id: int) -> int:
    return sum(1 for _ in _decoded_sessions(user_id))


def list_user_sessions(user_id: int, current_session_key: str | None = None) -> list[dict[str, object]]:
    """Строки карточки «Активные сессии»: устройство, адрес, когда активна."""
    items = []
    for session, data in _decoded_sessions(user_id):
        agent = str(data.get(SESSION_AGENT_KEY, ""))
        items.append(
            {
                "id": session.session_key[:12],
                "device": describe_agent(agent),
                "kind": device_kind(agent),
                "address": mask_ip(str(data.get(SESSION_IP_KEY, ""))),
                "startedAt": data.get(SESSION_STARTED_KEY),
                "lastSeenAt": data.get(SESSION_SEEN_KEY),
                "current": session.session_key == current_session_key,
            }
        )
    # Текущая сессия первой, дальше — по свежести активности.
    items.sort(key=lambda item: str(item["lastSeenAt"] or ""), reverse=True)
    items.sort(key=lambda item: not item["current"])
    return items


def revoke_user_sessions(user_id: int, *, except_session_key: str | None = None) -> int:
    """Delete all server-side sessions of a user, optionally keeping one (e.g. the current request)."""
    revoked = 0
    for session, _data in _decoded_sessions(user_id):
        if except_session_key is not None and session.session_key == except_session_key:
            continue
        session.delete()
        revoked += 1
    return revoked
