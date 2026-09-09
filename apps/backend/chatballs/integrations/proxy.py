"""Единый HTTP-opener с поддержкой прокси для всех интеграций (ADR-CHATBALLS-0020).

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

from chatballs.i18n import t
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


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Проверяет каждый Location, а не только исходный адрес.

    Политика исходящих (``integrations.outbound``) проверяет адрес до запроса.
    Но urllib сам ходит по редиректам, и ответ подставного провайдера мог
    вернуть 302 на ``http://169.254.169.254/…`` — проверку прошёл один адрес,
    а сходили по другому.

    Проверка стоит в ``http_error_302``, а не только в ``redirect_request``:
    свою проверку схемы urllib делает раньше и отвечает на неё ``HTTPError``,
    из-за чего запрет выглядел бы сетевой ошибкой, а не отказом политики.
    """

    def __init__(self, validate) -> None:
        self._validate = validate

    def http_error_302(self, req, fp, code, msg, headers):  # noqa: ANN001
        location = headers.get("location") or headers.get("uri") or ""
        if location:
            self._validate(urllib.parse.urljoin(req.full_url, location))
        return super().http_error_302(req, fp, code, msg, headers)

    # urllib связывает остальные коды с базовым методом на этапе создания
    # класса, поэтому переопределения одного http_error_302 мало.
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        self._validate(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _blocked_scheme_handlers() -> list[urllib.request.BaseHandler]:
    """Заглушки вместо file/ftp/data.

    ``build_opener`` ставит эти обработчики всегда, и убрать их нельзя — можно
    только подменить: наследника он предпочитает штатному классу. Без подмены
    любой адрес из ответа провайдера открывает локальный файл, а редирект на
    ``ftp://`` штатный urllib пропускает. Проверка схемы в вызывающем коде
    остаётся, но опирается на неё одну не стоит: сюда ходят четыре модуля.
    """
    return [_RefusedFileHandler(), _RefusedFTPHandler(), _RefusedDataHandler()]


def build_opener(proxy_url: str, *, validate_redirect=None):
    """urllib opener, проксирующий http/https/socks5 запросы.

    Пустой ``proxy_url`` → без прокси. ``validate_redirect`` — проверка адреса,
    на который ответ просит перейти: её передают там, где сам адрес пришёл
    данными от провайдера, а не из настроек подключения.
    """
    blocked = _blocked_scheme_handlers()
    if validate_redirect is not None:
        blocked.append(_GuardedRedirectHandler(validate_redirect))
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
        raise ValueError(t("settings.socks_needs_pysocks")) from error


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
