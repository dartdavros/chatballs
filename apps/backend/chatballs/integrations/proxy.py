"""Единый HTTP-opener с поддержкой прокси для всех интеграций (ADR-HUB-0020).

Поддерживаемые схемы proxy_url:
- http://[user:pass@]host:port
- https://[user:pass@]host:port
- socks5://[user:pass@]host:port   (DNS резолвится локально)
- socks5h://[user:pass@]host:port  (DNS через прокси, rdns=True)

HTTP/HTTPS работают через stdlib ProxyHandler. SOCKS5 требует PySocks (`socks`):
если зависимость отсутствует — SOCKS-схема даёт ValueError, чтобы владелец видел
явную ошибку, а не молчаливый обход прокси.
"""

from __future__ import annotations

import http.client
import ssl
import urllib.parse
import urllib.request

from chatballs.integrations.outbound import OutboundUrlRejected

SOCKS_SCHEMES = ("socks5", "socks5h")


class _RefusedFileHandler(urllib.request.FileHandler):
    def file_open(self, req):
        raise OutboundUrlRejected("Схема file:// в исходящих запросах запрещена")


class _RefusedFTPHandler(urllib.request.FTPHandler):
    def ftp_open(self, req):
        raise OutboundUrlRejected("Схема ftp:// в исходящих запросах запрещена")


class _RefusedDataHandler(urllib.request.DataHandler):
    def data_open(self, req):
        raise OutboundUrlRejected("Схема data: в исходящих запросах запрещена")


def _blocked_scheme_handlers() -> list[urllib.request.BaseHandler]:
    """Заглушки вместо file/ftp/data.

    ``build_opener`` ставит эти обработчики всегда, и убрать их нельзя — можно
    только подменить: наследника он предпочитает штатному классу. Без подмены
    любой адрес из ответа провайдера открывает локальный файл, а редирект на
    ``ftp://`` штатный urllib пропускает. Проверка схемы в вызывающем коде
    остаётся, но опирается на неё одну не стоит: сюда ходят четыре модуля.
    """
    return [_RefusedFileHandler(), _RefusedFTPHandler(), _RefusedDataHandler()]


def build_opener(proxy_url: str):
    """urllib opener, проксирующий http/https/socks5 запросы. Пустой proxy_url → без прокси."""
    blocked = _blocked_scheme_handlers()
    if not proxy_url:
        return urllib.request.build_opener(*blocked)
    scheme = urllib.parse.urlparse(proxy_url).scheme.lower()
    if scheme in SOCKS_SCHEMES:
        return urllib.request.build_opener(_SocksProxyHandler(proxy_url), *blocked)
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}), *blocked
    )


class _SocksProxyHandler(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
    """urllib handler, устанавливающий TCP-соединение через SOCKS5 (PySocks).

    PySocks патчит socket.create_connection глобально; мы вместо этого строим
    http.client-соединение с переопределённым .connect(), который туннелирует
    через SOCKS — это изолирует прокси от остального процесса.
    """

    def __init__(self, proxy_url: str):
        super().__init__()
        self._socks = _import_socks()
        parsed = urllib.parse.urlparse(proxy_url)
        self._proxy_type = self._socks.PROXY_TYPE_SOCKS5
        self._proxy_host = parsed.hostname or ""
        self._proxy_port = parsed.port or 1080
        self._username = parsed.username or None
        self._password = parsed.password or None
        # socks5h → DNS резолвится на стороне прокси (rdns=True).
        self._rdns = parsed.scheme.lower() == "socks5h"

    def http_open(self, req):
        return self.do_open(self._make_http_conn, req)

    def https_open(self, req):
        return self.do_open(self._make_https_conn, req)

    def _make_http_conn(self, req, timeout=30):
        host = req.host
        port = req.port or 80
        return _SocksHTTPConnection(host, port, self, timeout=timeout)

    def _make_https_conn(self, req, timeout=30):
        host = req.host
        port = req.port or 443
        return _SocksHTTPSConnection(host, port, self, timeout=timeout, context=ssl.create_default_context())

    def open_socket(self, host: str, port: int):
        return self._socks.create_connection(
            (host, port),
            proxy_type=self._proxy_type,
            proxy_addr=self._proxy_host,
            proxy_port=self._proxy_port,
            proxy_username=self._username,
            proxy_password=self._password,
            rdns=self._rdns,
        )


def _import_socks():
    try:
        import socks

        return socks
    except ImportError as error:
        raise ValueError("Для SOCKS-прокси нужна зависимость PySocks (pip install PySocks)") from error


class _SocksHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, handler, timeout=30):
        super().__init__(host, port, timeout=timeout)
        self._handler = handler

    def connect(self):
        self.sock = self._handler.open_socket(self.host, self.port)


class _SocksHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, handler, timeout=30, context=None):
        super().__init__(host, port, timeout=timeout, context=context)
        self._handler = handler

    def connect(self):
        sock = self._handler.open_socket(self.host, self.port)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
