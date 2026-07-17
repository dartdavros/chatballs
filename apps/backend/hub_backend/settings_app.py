# ruff: noqa: F403,F405
import os

from django.core.exceptions import ImproperlyConfigured

from hub_backend.settings_base import *

CUS_RUNTIME_SURFACE = "app"
ROOT_URLCONF = "hub_backend.urls_app"
ASGI_APPLICATION = "hub_backend.asgi_app.application"
WSGI_APPLICATION = "hub_backend.wsgi_app.application"

_app_hosts = os.environ.get("CUSTOCRM_APP_ALLOWED_HOSTS", "")
if not DEBUG and not TESTING and not _app_hosts:
    raise ImproperlyConfigured("CUSTOCRM_APP_ALLOWED_HOSTS is required for the app surface")
ALLOWED_HOSTS = env_list(
    "CUSTOCRM_APP_ALLOWED_HOSTS",
    env_list("CUS_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "app.localhost"]),
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CUSTOCRM_APP_CSRF_TRUSTED_ORIGINS",
    env_list("CUS_CSRF_TRUSTED_ORIGINS", []),
)

SESSION_COOKIE_NAME = os.environ.get(
    "CUSTOCRM_APP_SESSION_COOKIE_NAME",
    "__Host-custocrm-app-session" if SESSION_COOKIE_SECURE else "custocrm_app_session",
)
CSRF_COOKIE_NAME = os.environ.get(
    "CUSTOCRM_APP_CSRF_COOKIE_NAME",
    "__Host-custocrm-app-csrf" if CSRF_COOKIE_SECURE else "custocrm_app_csrftoken",
)
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"

CUS_PUBLIC_BASE_URL = os.environ.get("CUSTOCRM_APP_PUBLIC_BASE_URL", CUS_PUBLIC_BASE_URL)
CUS_CONTENT_SECURITY_POLICY = os.environ.get(
    "CUSTOCRM_APP_CSP",
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
)
