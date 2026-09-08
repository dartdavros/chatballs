# ruff: noqa: F403,F405
import os

from chatballs_backend.settings_base import *

CHATBALLS_RUNTIME_SURFACE = "admin"
ROOT_URLCONF = "chatballs_backend.urls_admin"
ASGI_APPLICATION = "chatballs_backend.asgi_admin.application"
WSGI_APPLICATION = "chatballs_backend.wsgi_admin.application"

# ADR-CHATBALLS-0031: admin доступен только через loopback bind и SSH tunnel.
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = []
CORS_ALLOWED_ORIGINS = []
SESSION_COOKIE_SECURE = env_bool("CHATBALLS_ADMIN_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SESSION_COOKIE_NAME = os.environ.get("CHATBALLS_ADMIN_SESSION_COOKIE_NAME", "chatballs_admin_session")
CSRF_COOKIE_NAME = os.environ.get("CHATBALLS_ADMIN_CSRF_COOKIE_NAME", "chatballs_admin_csrftoken")
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"
SECURE_SSL_REDIRECT = env_bool("CHATBALLS_ADMIN_SSL_REDIRECT", False)

CHATBALLS_CONTENT_SECURITY_POLICY = os.environ.get(
    "CHATBALLS_ADMIN_CSP",
    "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
    "form-action 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'",
)
