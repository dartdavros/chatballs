# ruff: noqa: F403,F405
import os

from chatballs_backend.settings_base import *

CHATBALLS_RUNTIME_SURFACE = "platform"
ROOT_URLCONF = "chatballs_backend.urls_platform"
ASGI_APPLICATION = "chatballs_backend.asgi_platform.application"
WSGI_APPLICATION = "chatballs_backend.wsgi_platform.application"

# Домены установки задаются в UI (мастер первого запуска), а не переменной
# окружения: коробка поднимается одной командой и до настройки отвечает на
# локальные адреса. Проверку хоста несёт middleware/список ниже.
ALLOWED_HOSTS = env_list(
    "CHATBALLS_PLATFORM_ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "platform.localhost"],
)
if "backend-platform" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("backend-platform")
CSRF_TRUSTED_ORIGINS = env_list("CHATBALLS_PLATFORM_CSRF_TRUSTED_ORIGINS", [])
CORS_ALLOWED_ORIGINS = []

# Caddy спрашивает разрешение на on-demand сертификат Help Center по plain HTTP
# из внутренней сети: заголовок X-Forwarded-Proto он не шлёт и по редиректам не
# ходит. Без исключения SECURE_SSL_REDIRECT отвечает 301, Caddy считает домен
# неавторизованным и сертификат портала не выпускается.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/gateway/"]

SESSION_COOKIE_NAME = os.environ.get(
    "CHATBALLS_PLATFORM_SESSION_COOKIE_NAME",
    "__Host-chatballs-platform-session"
    if SESSION_COOKIE_SECURE
    else "chatballs_platform_session",
)
CSRF_COOKIE_NAME = os.environ.get(
    "CHATBALLS_PLATFORM_CSRF_COOKIE_NAME",
    "__Host-chatballs-platform-csrf"
    if CSRF_COOKIE_SECURE
    else "chatballs_platform_csrftoken",
)
# Имя cookie по http и его защищённая пара для запросов по TLS.
# Переключает TlsAwareCookieMiddleware по факту протокола запроса — тем же
# правилом, что и фронтенд (api/client.ts).
CHATBALLS_TLS_COOKIE_NAMES = {
    SESSION_COOKIE_NAME: "__Host-chatballs-platform-session",
    CSRF_COOKIE_NAME: "__Host-chatballs-platform-csrf",
}

SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"

CHATBALLS_CONTENT_SECURITY_POLICY = os.environ.get(
    "CHATBALLS_PLATFORM_CSP",
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
)
