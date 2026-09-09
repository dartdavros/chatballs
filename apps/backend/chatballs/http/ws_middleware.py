"""ASGI-обвязка WebSocket: имена cookie по факту TLS и проверка Origin.

HTTP-слой продукта переименовывает cookie по протоколу запроса
(``chatballs.http.middleware.TlsAwareCookieMiddleware``): по https браузер
держит ``__Host-…``, по http — обычное имя. Django-middleware на
WebSocket-хендшейк не выполняется, а Channels ищет cookie строго по
``settings.SESSION_COOKIE_NAME``. Из-за этого на установке с TLS сокет не
находил сессию вообще: браузер присылал только защищённое имя, и каждое
подключение закрывалось как неаутентифицированное — живые обновления диалогов
молча переставали работать.

Здесь то же правило применяется к scope до ``AuthMiddlewareStack``.
"""

from __future__ import annotations

from collections.abc import Callable
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

from django.conf import settings


def _tls_cookie_pairs() -> tuple[tuple[str, str], ...]:
    mapping = getattr(settings, "CHATBALLS_TLS_COOKIE_NAMES", {})
    return tuple((plain, hardened) for plain, hardened in mapping.items() if plain != hardened)


def _header(scope: dict, name: bytes) -> bytes:
    for key, value in scope.get("headers") or ():
        if key.lower() == name:
            return value
    return b""


def _replace_header(scope: dict, name: bytes, value: bytes) -> None:
    headers = [(key, item) for key, item in (scope.get("headers") or ()) if key.lower() != name]
    if value:
        headers.append((name, value))
    scope["headers"] = headers


class TlsAwareCookieASGIMiddleware:
    """По wss отдаёт вглубь защищённые cookie под обычными именами."""

    def __init__(self, inner: Callable) -> None:
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "websocket" and scope.get("scheme") in {"wss", "https"}:
            self._rewrite(scope)
        return await self.inner(scope, receive, send)

    @staticmethod
    def _rewrite(scope: dict) -> None:
        pairs = _tls_cookie_pairs()
        if not pairs:
            return
        raw = _header(scope, b"cookie")
        if not raw:
            return
        jar = SimpleCookie()
        jar.load(raw.decode("latin-1"))
        values = {key: morsel.value for key, morsel in jar.items()}
        changed = False
        for plain, hardened in pairs:
            if hardened in values:
                # Защищённое имя всегда сильнее обычного — то же правило, что и
                # в HTTP-слое: cookie с префиксом __Host- браузер принимает
                # только с самого хоста и только по TLS.
                if values.get(plain) != values[hardened]:
                    values[plain] = values[hardened]
                    changed = True
            elif plain in values:
                # По TLS обычное имя мы не выдаём — значит пришло не от нас.
                del values[plain]
                changed = True
        if not changed:
            return
        rebuilt = "; ".join(f"{key}={value}" for key, value in values.items())
        _replace_header(scope, b"cookie", rebuilt.encode("latin-1"))


class SameOriginWebSocketMiddleware:
    """Отклоняет хендшейк, у которого Origin не совпадает с Host.

    Сокет открывает то же SPA, что и REST, поэтому Origin у него всегда наш.
    Кросс-сайтовый запрос сейчас и так остаётся без cookie (``SameSite=Lax``),
    но полагаться на один барьер не стоит: у cookie этот флаг настраиваемый.
    Клиенты без браузера Origin не присылают — их не трогаем.
    """

    def __init__(self, inner: Callable) -> None:
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "websocket" and not self._allowed(scope):
            await send({"type": "websocket.close", "code": 4403})
            return
        return await self.inner(scope, receive, send)

    @staticmethod
    def _allowed(scope: dict) -> bool:
        origin = _header(scope, b"origin").decode("latin-1").strip()
        if not origin:
            return True
        host = _header(scope, b"host").decode("latin-1").strip().lower()
        if not host:
            return False
        origin_host = (urlsplit(origin).netloc or "").lower()
        return origin_host == host


def websocket_boundary(inner: Callable) -> Callable:
    """Обе проверки одним вызовом — порядок важен, Origin проверяется первым."""

    return SameOriginWebSocketMiddleware(TlsAwareCookieASGIMiddleware(inner))
