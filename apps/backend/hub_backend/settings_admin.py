# ruff: noqa: F403,F405
import os

from hub_backend.settings_base import *

HUB_RUNTIME_SURFACE = "admin"
ROOT_URLCONF = "hub_backend.urls_admin"
ASGI_APPLICATION = "hub_backend.asgi_admin.application"
WSGI_APPLICATION = "hub_backend.wsgi_admin.application"

# ADR-HUB-0031: admin доступен только через loopback bind и SSH tunnel.
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = []
CORS_ALLOWED_ORIGINS = []
SESSION_COOKIE_SECURE = env_bool("CUSTOCRM_ADMIN_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SESSION_COOKIE_NAME = os.environ.get("CUSTOCRM_ADMIN_SESSION_COOKIE_NAME", "custocrm_admin_session")
CSRF_COOKIE_NAME = os.environ.get("CUSTOCRM_ADMIN_CSRF_COOKIE_NAME", "custocrm_admin_csrftoken")
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"
SECURE_SSL_REDIRECT = env_bool("CUSTOCRM_ADMIN_SSL_REDIRECT", False)

HUB_CONTENT_SECURITY_POLICY = os.environ.get(
    "CUSTOCRM_ADMIN_CSP",
    "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
    "form-action 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'",
)
