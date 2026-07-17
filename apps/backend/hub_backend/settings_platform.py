# ruff: noqa: F403,F405
import os

from django.core.exceptions import ImproperlyConfigured

from hub_backend.settings_base import *

CUS_RUNTIME_SURFACE = "platform"
ROOT_URLCONF = "hub_backend.urls_platform"
ASGI_APPLICATION = "hub_backend.asgi_platform.application"
WSGI_APPLICATION = "hub_backend.wsgi_platform.application"

_platform_hosts = os.environ.get("CUSTOCRM_PLATFORM_ALLOWED_HOSTS", "")
if not DEBUG and not TESTING and not _platform_hosts:
    raise ImproperlyConfigured(
        "CUSTOCRM_PLATFORM_ALLOWED_HOSTS is required for the platform surface"
    )
ALLOWED_HOSTS = env_list(
    "CUSTOCRM_PLATFORM_ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", "platform.localhost"],
)
CSRF_TRUSTED_ORIGINS = env_list("CUSTOCRM_PLATFORM_CSRF_TRUSTED_ORIGINS", [])
CORS_ALLOWED_ORIGINS = []

SESSION_COOKIE_NAME = os.environ.get(
    "CUSTOCRM_PLATFORM_SESSION_COOKIE_NAME",
    "__Host-custocrm-platform-session"
    if SESSION_COOKIE_SECURE
    else "custocrm_platform_session",
)
CSRF_COOKIE_NAME = os.environ.get(
    "CUSTOCRM_PLATFORM_CSRF_COOKIE_NAME",
    "__Host-custocrm-platform-csrf"
    if CSRF_COOKIE_SECURE
    else "custocrm_platform_csrftoken",
)
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"

CUS_CONTENT_SECURITY_POLICY = os.environ.get(
    "CUSTOCRM_PLATFORM_CSP",
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
)
