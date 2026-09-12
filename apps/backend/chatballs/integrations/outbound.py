"""Политика исходящих запросов интеграций: какие адреса хабу открывать можно.

Адреса приходят из двух разных мест, и доверие к ним разное.

Настройку (``base_url``, ``proxy_url``) вводит владелец организации, и он
вправе указать хост внутри своей сети: self-hosted ставят рядом локальный
OpenAI-совместимый сервер или собственный Bot API. Поэтому у настройки
проверяется только схема — запрещать приватные адреса значило бы ломать
документированный сценарий.

А адреса из ответов провайдера — данные, а не настройка. Ответ подставного
``base_url`` может назвать внутренний адрес, и хаб сходит по нему своими руками
(SSRF), либо ``file:///run/chatballs/secrets/secret_key`` — и содержимое
секрета осядет вложением в диалоге. Такие адреса ограничены http/https и
публичными хостами; исключение — хост, который владелец сам указал в
``base_url`` этого подключения.
"""

from __future__ import annotations

from chatballs.i18n import t

import ipaddress
import socket
from urllib.parse import urlsplit

HTTP_SCHEMES = frozenset({"http", "https"})
PROXY_SCHEMES = frozenset({"http", "https", "socks5", "socks5h"})


class OutboundUrlRejected(ValueError):
    """Адрес не разрешён политикой исходящих запросов."""


def host_of(url: str) -> str:
    """Хост адреса в нижнем регистре; пусто, если адрес не разобрался."""
    return (urlsplit(str(url or "").strip()).hostname or "").lower()


def clean_config_url(value: str, *, schemes: frozenset[str]) -> str:
    """Адрес из настроек подключения: схема из списка и непустой хост.

    Приватные адреса здесь разрешены намеренно — см. модульный докстринг.
    """
    candidate = str(value or "").strip()
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in schemes or not parsed.hostname:
        allowed = ", ".join(f"{scheme}://" for scheme in sorted(schemes))
        raise OutboundUrlRejected(t("settings.url_scheme_required", schemes=allowed))
    return candidate


def ensure_downloadable(url: str, *, allowed_host: str = "", via_proxy: bool = False) -> None:
    """Проверить адрес, пришедший ответом провайдера, перед скачиванием.

    ``allowed_host`` — хост из ``base_url`` подключения: его владелец назвал
    сам, поэтому он разрешён, даже если ведёт внутрь сети.

    При настроенном прокси проверка хоста пропускается: до цели хаб идёт не
    сам, а через прокси владельца, и локальный резолвер (тем более при
    ``socks5h``, где DNS живёт на стороне прокси) о ней ничего не знает.
    """
    parsed = urlsplit(str(url or "").strip())
    scheme = parsed.scheme.lower()
    if scheme not in HTTP_SCHEMES or not parsed.hostname:
        raise OutboundUrlRejected(t("settings.download_http_only"))
    host = parsed.hostname.lower()
    if via_proxy or (allowed_host and host == allowed_host.lower()):
        return
    port = parsed.port or (443 if scheme == "https" else 80)
    if _resolves_to_private(host, port):
        raise OutboundUrlRejected(t("settings.url_points_inside"))


def _resolves_to_private(host: str, port: int) -> bool:
    """Ведёт ли хост на непубличный адрес.

    Проверка и последующее соединение резолвят имя порознь, поэтому от DNS
    rebinding она не спасает — для этого пришлось бы соединяться по уже
    проверенному адресу мимо urllib. Она закрывает прямое указание внутреннего
    адреса, а это и есть путь, которым сюда приходит подставной base_url.
    """
    try:
        return not ipaddress.ip_address(host).is_global
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError:
        # Имя не разрешилось — пропускаем. Соединение пойдёт через тот же
        # резолвер и упадёт там же, так что запрещать нечего; а отказ сделал бы
        # скачивание вложений заложником доступности DNS.
        return False
    return any(not ipaddress.ip_address(info[4][0]).is_global for info in infos)
