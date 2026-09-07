from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class LocalCorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        is_allowed_preflight = (
            request.method == "OPTIONS"
            and request.headers.get("Origin") in settings.CORS_ALLOWED_ORIGINS
        )
        if is_allowed_preflight:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        origin = request.headers.get("Origin")
        if origin in settings.CORS_ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Content-Type, X-Correlation-Id, X-CSRFToken"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Vary"] = "Origin"
        return response


class ContentSecurityPolicyMiddleware:
    """Apply the CSP selected by the current runtime surface."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        policy = settings.CHATBALLS_CONTENT_SECURITY_POLICY
        if policy and not response.has_header("Content-Security-Policy"):
            response["Content-Security-Policy"] = policy
        return response

class TlsAwareCookieMiddleware:
    """Жёсткость cookie по факту TLS, а не по переменной окружения.

    Коробку ставят одной командой и сначала открывают по http — по адресу
    сервера, до того как заведён домен и выписан сертификат. Если бы Secure-
    cookie и префикс ``__Host-`` включались настройкой, такая установка не
    смогла бы даже завести владельца в мастере. Поэтому решение принимается на
    каждый запрос: пришли по https — отдаём ``__Host-`` + Secure, пришли по
    http — обычное имя без Secure. Настраивать нечего, а установка сама
    ужесточается в тот момент, когда перед ней появляется TLS.

    Фронтенд выбирает имя cookie по протоколу страницы тем же правилом
    (``api/client.ts``), поэтому стороны всегда сходятся.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def _pairs(self) -> tuple[tuple[str, str], ...]:
        """Пары «имя по http» → «имя по https» из настроек поверхности.

        Имена заданы явно, а не собираются префиксом: их знает и фронтенд
        (api/client.ts), и они не должны разъезжаться.
        """
        mapping = getattr(settings, "CHATBALLS_TLS_COOKIE_NAMES", {})
        return tuple(
            (plain, hardened)
            for plain, hardened in mapping.items()
            if plain != hardened
        )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        secure = request.is_secure()
        pairs = self._pairs()
        if secure:
            # Браузер прислал защищённые имена — отдаём их Django под обычными.
            for plain, hardened in pairs:
                if hardened in request.COOKIES and plain not in request.COOKIES:
                    request.COOKIES[plain] = request.COOKIES[hardened]
        response = self.get_response(request)
        if not secure:
            return response
        for plain, hardened in pairs:
            cookie = response.cookies.get(plain)
            if cookie is None:
                continue
            response.cookies[hardened] = cookie.value
            target = response.cookies[hardened]
            for key, value in cookie.items():
                if value != "":
                    target[key] = value
            # Требования префикса __Host-: Secure, Path=/ и без Domain.
            target["secure"] = True
            target["path"] = "/"
            target["domain"] = ""
            del response.cookies[plain]
        return response
