# ruff: noqa: F403,F405
import os

from chatballs_backend.settings_base import *

CHATBALLS_RUNTIME_SURFACE = "app"
ROOT_URLCONF = "chatballs_backend.urls_app"
ASGI_APPLICATION = "chatballs_backend.asgi_app.application"
WSGI_APPLICATION = "chatballs_backend.wsgi_app.application"

# Домены установки задаются в UI (мастер первого запуска), а не переменной
# окружения: коробка поднимается одной командой и до настройки отвечает на
# локальные адреса. Проверку хоста несёт middleware/список ниже.
CHATBALLS_APP_PRIMARY_HOSTS = env_list(
    "CHATBALLS_APP_ALLOWED_HOSTS",
    env_list("CHATBALLS_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "app.localhost"]),
)
_help_host_pattern = f".{CHATBALLS_HELP_BASE_DOMAIN}"
if _help_host_pattern not in CHATBALLS_APP_PRIMARY_HOSTS:
    CHATBALLS_APP_PRIMARY_HOSTS.append(_help_host_pattern)
if TESTING and "testserver" not in CHATBALLS_APP_PRIMARY_HOSTS:
    CHATBALLS_APP_PRIMARY_HOSTS.append("testserver")
# Custom portal domains are checked against the published ingress directory by
# SupportPortalHostBoundaryMiddleware. Django's static list cannot express them.
ALLOWED_HOSTS = ["*"]
MIDDLEWARE.insert(
    1,
    "chatballs.support_portals.host_boundary.SupportPortalHostBoundaryMiddleware",
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CHATBALLS_APP_CSRF_TRUSTED_ORIGINS",
    env_list("CHATBALLS_CSRF_TRUSTED_ORIGINS", []),
)

SESSION_COOKIE_NAME = os.environ.get(
    "CHATBALLS_APP_SESSION_COOKIE_NAME",
    "__Host-chatballs-app-session" if SESSION_COOKIE_SECURE else "chatballs_app_session",
)
CSRF_COOKIE_NAME = os.environ.get(
    "CHATBALLS_APP_CSRF_COOKIE_NAME",
    "__Host-chatballs-app-csrf" if CSRF_COOKIE_SECURE else "chatballs_app_csrftoken",
)
# Имя cookie по http и его защищённая пара для запросов по TLS.
# Переключает TlsAwareCookieMiddleware по факту протокола запроса — тем же
# правилом, что и фронтенд (api/client.ts).
CHATBALLS_TLS_COOKIE_NAMES = {
    SESSION_COOKIE_NAME: "__Host-chatballs-app-session",
    CSRF_COOKIE_NAME: "__Host-chatballs-app-csrf",
}

SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"

CHATBALLS_PUBLIC_BASE_URL = os.environ.get("CHATBALLS_APP_PUBLIC_BASE_URL", CHATBALLS_PUBLIC_BASE_URL)
CHATBALLS_CONTENT_SECURITY_POLICY = os.environ.get(
    "CHATBALLS_APP_CSP",
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
)
