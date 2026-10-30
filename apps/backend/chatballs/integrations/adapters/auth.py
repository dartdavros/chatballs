"""Расширения авторизации (SPEC-0037 R-7; ADR-0038 п.3).

Расширение знает, как секреты способа доступа попадают в запрос: заголовок
ключа, Basic/Bearer, токен OAuth, подпись, клиентский сертификат или секрет
в самом адресе. Адаптер выбирает расширение ссылкой «ключ@версия» и задаёт
ему параметры. Секреты есть только в памяти сервера на время запроса.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from chatballs.integrations.adapters.registry import Extension
from chatballs.integrations.adapters.schema import TypeSpec


@dataclass(frozen=True)
class OutboundRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    # PEM сертификата и ключа клиента для взаимного TLS.
    client_certificate: tuple[str, str] | None = None


class AuthExtension:
    """База: секрет не добавляется, адрес берётся из настроек подключения."""

    def prepare(self, request: OutboundRequest, credentials: dict[str, Any], options: dict[str, Any]) -> OutboundRequest:
        return request

    def base_url(self, settings: dict[str, Any], credentials: dict[str, Any], options: dict[str, Any]) -> str:
        return str(settings.get(options.get("base_url_field", "base_url"), "") or options.get("base_url", ""))

    def host(self, settings: dict[str, Any], credentials: dict[str, Any], options: dict[str, Any]) -> str:
        return urlsplit(self.base_url(settings, credentials, options)).hostname or ""

    def secrets(self, credentials: dict[str, Any]) -> list[str]:
        return credential_strings(credentials)


class ApiKeyAuth(AuthExtension):
    """Ключ в заголовке (по умолчанию) или в параметре адреса."""

    def prepare(self, request, credentials, options):
        key = str(credentials.get("key", ""))
        if options.get("in") == "query":
            return replace(request, url=_with_query(request.url, {options.get("name", "api_key"): key}))
        header = options.get("name", "X-API-Key")
        prefix = options.get("prefix", "")
        return replace(request, headers={**request.headers, header: f"{prefix}{key}"})


class BasicAuth(AuthExtension):
    def prepare(self, request, credentials, options):
        pair = f"{credentials.get('username', '')}:{credentials.get('password', '')}".encode()
        token = base64.b64encode(pair).decode("ascii")
        return replace(request, headers={**request.headers, "Authorization": f"Basic {token}"})


class BearerAuth(AuthExtension):
    field_name = "token"

    def prepare(self, request, credentials, options):
        token = str(credentials.get(self.field_name, ""))
        return replace(request, headers={**request.headers, "Authorization": f"Bearer {token}"})


class OAuth2Auth(BearerAuth):
    """Токен доступа OAuth 2.0; вход и обновление — service_connections.auth."""

    field_name = "access_token"


class HmacSignatureAuth(AuthExtension):
    """Подпись запроса общим секретом: метка времени и HMAC тела."""

    def prepare(self, request, credentials, options):
        secret = str(credentials.get("secret", "")).encode()
        timestamp = str(int(time.time()))
        path = urlsplit(request.url).path or "/"
        message = b"\n".join([request.method.upper().encode(), path.encode(), timestamp.encode(), request.body or b""])
        algorithm = getattr(hashlib, options.get("algorithm", "sha256"))
        signature = hmac.new(secret, message, algorithm).hexdigest()
        headers = {
            **request.headers,
            options.get("timestamp_header", "X-Timestamp"): timestamp,
            options.get("signature_header", "X-Signature"): signature,
        }
        return replace(request, headers=headers)


class ClientCertificateAuth(AuthExtension):
    def prepare(self, request, credentials, options):
        pair = (str(credentials.get("certificate", "")), str(credentials.get("private_key", "")))
        return replace(request, client_certificate=pair)


class SecretUrlAuth(AuthExtension):
    """Секрет — часть адреса (например, входящий вебхук): адрес и есть доступ."""

    def base_url(self, settings, credentials, options):
        return str(credentials.get("url", "")).rstrip("/") + "/"

    def host(self, settings, credentials, options):
        return urlsplit(str(credentials.get("url", ""))).hostname or ""


def split_values(fields: TypeSpec, values: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Разделить введённое на несекретные настройки и секреты по схеме полей."""

    settings: dict[str, Any] = {}
    credentials: dict[str, Any] = {}
    for name, spec in fields.properties:
        if name not in values:
            continue
        value = values[name].strip() if isinstance(values[name], str) else values[name]
        # Вложенный секрет защищает всю ветвь: структура и соседние значения
        # сохраняются, но ни одна часть ветви не попадёт в открытый JSON.
        (credentials if contains_secret(spec) else settings)[name] = value
    return settings, credentials


def contains_secret(spec: TypeSpec) -> bool:
    return spec.secret or any(contains_secret(child) for _, child in spec.properties) or (
        spec.items is not None and contains_secret(spec.items)
    )


def credential_strings(value: Any) -> list[str]:
    """Все строковые значения credentials, включая вложенные объекты/списки."""

    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, dict):
        return [secret for child in value.values() for secret in credential_strings(child)]
    if isinstance(value, list | tuple):
        return [secret for child in value for secret in credential_strings(child)]
    return []


def _with_query(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = "&".join(item for item in (parts.query, urlencode(params)) if item)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def builtin_extensions() -> list[Extension]:
    implementations = {
        "api_key": ApiKeyAuth(),
        "basic": BasicAuth(),
        "bearer": BearerAuth(),
        "oauth2": OAuth2Auth(),
        "hmac_signature": HmacSignatureAuth(),
        "client_certificate": ClientCertificateAuth(),
        "secret_url": SecretUrlAuth(),
        "none": AuthExtension(),
    }
    return [Extension("auth", key, 1, implementation) for key, implementation in implementations.items()]
