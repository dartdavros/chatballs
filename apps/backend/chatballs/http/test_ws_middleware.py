"""WebSocket-обвязка: имена cookie по TLS и проверка Origin.

Установка с сертификатом отдаёт браузеру только ``__Host-``-имена, а Channels
ищет сессию строго по ``settings.SESSION_COOKIE_NAME``. Пока это не сходилось,
каждый сокет на https закрывался как неаутентифицированный — и живые
обновления диалогов молча не работали, притом что REST на той же странице
работал.
"""

from __future__ import annotations

import asyncio

from django.test import SimpleTestCase, override_settings

from chatballs.http.ws_middleware import (
    SameOriginWebSocketMiddleware,
    TlsAwareCookieASGIMiddleware,
)

PLAIN = "chatballs_app_session"
HARDENED = "__Host-chatballs-app-session"
COOKIE_NAMES = {PLAIN: HARDENED, "chatballs_app_csrftoken": "__Host-chatballs-app-csrf"}


class _Recorder:
    """Внутреннее приложение: запоминает scope, до которого дошёл запрос."""

    def __init__(self) -> None:
        self.scope: dict | None = None

    async def __call__(self, scope, receive, send):
        self.scope = scope


def _scope(*, scheme: str = "wss", cookie: str = "", origin: str = "", host: str = "app.example") -> dict:
    headers = [(b"host", host.encode())]
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    if origin:
        headers.append((b"origin", origin.encode()))
    return {"type": "websocket", "scheme": scheme, "headers": headers}


def _cookies(scope: dict) -> dict[str, str]:
    raw = next((value for key, value in scope["headers"] if key == b"cookie"), b"")
    items = [part.strip() for part in raw.decode().split(";") if part.strip()]
    return dict(item.split("=", 1) for item in items)


@override_settings(CHATBALLS_TLS_COOKIE_NAMES=COOKIE_NAMES)
class TlsAwareCookieASGIMiddlewareTests(SimpleTestCase):
    def _run(self, scope: dict) -> dict:
        inner = _Recorder()
        asyncio.run(TlsAwareCookieASGIMiddleware(inner)(scope, None, None))
        assert inner.scope is not None
        return inner.scope

    def test_hardened_cookie_is_delivered_under_the_plain_name(self) -> None:
        scope = self._run(_scope(cookie=f"{HARDENED}=session-value"))

        self.assertEqual(_cookies(scope)[PLAIN], "session-value")

    def test_plain_cookie_alone_is_dropped_over_tls(self) -> None:
        """По TLS обычное имя мы не выдаём — значит пришло оно не от нас."""
        scope = self._run(_scope(cookie=f"{PLAIN}=planted"))

        self.assertNotIn(PLAIN, _cookies(scope))

    def test_hardened_cookie_wins_over_a_planted_plain_one(self) -> None:
        scope = self._run(_scope(cookie=f"{PLAIN}=planted; {HARDENED}=real"))

        self.assertEqual(_cookies(scope)[PLAIN], "real")

    def test_plain_http_scope_is_untouched(self) -> None:
        scope = self._run(_scope(scheme="ws", cookie=f"{PLAIN}=session-value"))

        self.assertEqual(_cookies(scope)[PLAIN], "session-value")

    def test_scope_without_cookies_passes_through(self) -> None:
        scope = self._run(_scope())

        self.assertEqual(_cookies(scope), {})


class SameOriginWebSocketMiddlewareTests(SimpleTestCase):
    def _run(self, scope: dict) -> tuple[dict | None, list[dict]]:
        inner = _Recorder()
        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        asyncio.run(SameOriginWebSocketMiddleware(inner)(scope, None, send))
        return inner.scope, sent

    def test_same_origin_handshake_passes(self) -> None:
        scope, sent = self._run(_scope(origin="https://app.example", host="app.example"))

        self.assertIsNotNone(scope)
        self.assertEqual(sent, [])

    def test_foreign_origin_is_closed(self) -> None:
        scope, sent = self._run(_scope(origin="https://evil.example", host="app.example"))

        self.assertIsNone(scope)
        self.assertEqual(sent, [{"type": "websocket.close", "code": 4403}])

    def test_origin_with_matching_port_passes(self) -> None:
        scope, sent = self._run(
            _scope(origin="http://localhost:5173", host="localhost:5173")
        )

        self.assertIsNotNone(scope)
        self.assertEqual(sent, [])

    def test_client_without_origin_is_allowed(self) -> None:
        """Origin шлёт браузер; клиенты без него — не то, от чего мы защищаемся."""
        scope, sent = self._run(_scope(host="app.example"))

        self.assertIsNotNone(scope)
        self.assertEqual(sent, [])
