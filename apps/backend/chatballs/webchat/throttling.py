"""Лимиты публичных endpoint'ов виджета (SPEC-CHATBALLS-0003 §7).

Виджет открыт миру: сессию заводит и сообщения шлёт аноним, без входа и без
CSRF. Каждое сообщение — ход AI по ключу организации (ingest вызывает
провайдера прямо в запросе), каждый файл — место в её хранилище. Без лимитов
один скрипт тратит чужие деньги и диск, а поток порождённых событий вдобавок
вытесняет из воркера поллинг мессенджеров и таймауты звонков.

Контуров два, и они дополняют друг друга:

- по адресу клиента — единственное, что есть у того, у кого сессии ещё нет
  (выдача сессий, чтение конфигурации), и грубый потолок на вал запросов;
- по токену сессии — за NAT адрес общий: лимит по нему либо бьёт по соседям,
  либо бесполезен. Счётчик по токену считает того, кто действительно шлёт, и
  не обнуляется сменой адреса.

Ограничение по доменам (``allowed_origins``) лимитов не заменяет: origin
страницы-хозяина виджет заявляет сам, см. ``api_inputs.host_origin``.
"""

from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle

from chatballs.webchat.api_inputs import bearer_token
from chatballs.webchat.services import hash_session_token


class _WebchatThrottle(SimpleRateThrottle):
    """Scope выбирается по запросу, поэтому rate читается не в ``__init__``.

    Тот же приём, что у DRF в ``ScopedRateThrottle``: базовый ``__init__``
    требует scope заранее, а он у нас зависит от метода и типа содержимого.
    """

    def __init__(self) -> None:
        pass

    def scope_for(self, request) -> str:
        raise NotImplementedError

    def allow_request(self, request, view):
        scope = self.scope_for(request)
        if not scope:
            return True
        self.scope = scope
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)


class _ClientThrottle(_WebchatThrottle):
    """Счётчик по адресу клиента."""

    scopes: dict[str, str] = {}

    def scope_for(self, request) -> str:
        return self.scopes.get(request.method, "")

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class WebchatConfigThrottle(_ClientThrottle):
    """Чтение публичной конфигурации виджета."""

    scopes = {"GET": "webchat_config"}


class WebchatSessionIssueThrottle(_ClientThrottle):
    """Выдача анонимных сессий: каждая — новые Contact, Identity и WebSession."""

    scopes = {"POST": "webchat_session"}


class WebchatTrafficThrottle(_ClientThrottle):
    """Поллинг и отдача файлов — щедро, отправка — строже."""

    scopes = {"GET": "webchat_read", "POST": "webchat_write"}


class WebchatSessionTrafficThrottle(_WebchatThrottle):
    """Счётчик по токену сессии: отдельно чтение, отправка и загрузка файлов."""

    def scope_for(self, request) -> str:
        if request.method == "GET":
            return "webchat_session_read"
        if (request.content_type or "").startswith("multipart/form-data"):
            return "webchat_session_upload"
        return "webchat_session_write"

    def get_cache_key(self, request, view) -> str | None:
        token = bearer_token(request)
        # Без токена считать нечего: такой запрос всё равно отобьёт
        # resolve_session, а по адресу его уже посчитал WebchatTrafficThrottle.
        if not token:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": hash_session_token(token),
        }
