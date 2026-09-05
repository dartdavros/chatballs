# ruff: noqa: F403,F405
import os

from django.core.exceptions import ImproperlyConfigured

from chatballs_backend.settings_base import *

CHATBALLS_RUNTIME_SURFACE = "platform"
ROOT_URLCONF = "chatballs_backend.urls_platform"
ASGI_APPLICATION = "chatballs_backend.asgi_platform.application"
WSGI_APPLICATION = "chatballs_backend.wsgi_platform.application"

_platform_hosts = os.environ.get("CHATBALLS_PLATFORM_ALLOWED_HOSTS", "")
if not DEBUG and not TESTING and not _platform_hosts:
    raise ImproperlyConfigured(
        "CHATBALLS_PLATFORM_ALLOWED_HOSTS is required for the platform surface"
    )
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
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"

CHATBALLS_CONTENT_SECURITY_POLICY = os.environ.get(
    "CHATBALLS_PLATFORM_CSP",
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
)
