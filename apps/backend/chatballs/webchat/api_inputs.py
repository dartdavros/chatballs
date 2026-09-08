"""Разбор публичных запросов виджета: токен сессии и origin страницы-хозяина.

Модуль общий для views и throttling: лимит должен считаться по той же сессии,
по которой запрос потом резолвится, и не разъезжаться с ней.
"""

from __future__ import annotations

from urllib.parse import urlsplit

BEARER_PREFIX = "Bearer "


def bearer_token(request) -> str:
    """Токен сессии из заголовка или query — без разбора тела запроса.

    Лимиты считаются до того, как DRF прочитает тело: если доставать токен из
    multipart, двадцатимегабайтная загрузка успевала бы доехать до сервера
    прежде, чем её отобьёт лимит. Виджет шлёт токен заголовком (POST) либо
    параметром (<img>/<audio> заголовков не умеют).
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith(BEARER_PREFIX):
        return auth[len(BEARER_PREFIX) :]
    return request.GET.get("token", "")


def session_token(request) -> str:
    """Токен сессии, включая совместимость с передачей телом POST."""
    token = bearer_token(request)
    if token:
        return token
    if request.method == "POST":
        return str(request.data.get("token", ""))
    return ""


def _origin_of(url: str) -> str:
    """«https://host:port» из абсолютного URL; иначе пустая строка."""
    parsed = urlsplit(str(url).strip())
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def host_origin(request) -> str:
    """Origin страницы, на которой стоит виджет.

    Приоритет — у заголовков, которые проставляет сам браузер: страница их не
    подделает. Но виджет живёт в iframe на нашем же origin, и в его запросах
    браузер называет нас, а не сайт-хозяина; узнать хозяина оттуда нечем,
    кроме ``document.referrer``, который iframe присылает полем ``hostOrigin``.
    Поэтому поле читается только там, где заголовки указывают на нас самих, и
    никогда их не перебивает.

    ``hostOrigin`` — заявление клиента, а не доказательство. Ограничение по
    доменам (``WebChatWidget.allowed_origins``) держит встраивание виджета
    чужим сайтом в браузере — там его стерегут same-origin и отсутствие CORS,
    — но границей безопасности против скриптованного клиента не является: от
    злоупотреблений защищают лимиты (``webchat/throttling.py``).
    """
    own = _origin_of(request.build_absolute_uri("/"))
    for header in ("Origin", "Referer"):
        observed = _origin_of(request.headers.get(header, ""))
        if observed and observed != own:
            return observed
    claimed = (
        request.data.get("hostOrigin", "")
        if request.method == "POST"
        else request.GET.get("hostOrigin", "")
    )
    return str(claimed or "")
