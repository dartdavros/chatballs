import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

INSECURE_SECRET_KEY = "local-development-only"

# Автоопределение тестового прогона, чтобы manage.py test / pytest работали
# без ручного выставления production-окружения.
TESTING = "test" in sys.argv or "pytest" in sys.modules


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.environ.get("HUB_SECRET_KEY", INSECURE_SECRET_KEY)
DEBUG = env_bool("HUB_DEBUG")
ALLOWED_HOSTS = env_list("HUB_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list("HUB_CSRF_TRUSTED_ORIGINS", [])

# Запрещаем запуск в production с дефолтным/пустым ключом подписи.
if not DEBUG and not TESTING and SECRET_KEY in {"", INSECURE_SECRET_KEY}:
    raise ImproperlyConfigured("HUB_SECRET_KEY must be set to a strong value when HUB_DEBUG is disabled")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "hub_platform.identity",
    "hub_platform.products",
    "hub_platform.health",
    "hub_platform.events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "hub_platform.http.middleware.LocalCorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "hub_platform.events.middleware.CorrelationIdMiddleware",
]

ROOT_URLCONF = "hub_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hub_backend.wsgi.application"
ASGI_APPLICATION = "hub_backend.asgi.application"

AUTH_USER_MODEL = "identity.HumanUser"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "edevs_hub"),
        "USER": os.environ.get("POSTGRES_USER", "edevs_hub"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "edevs_hub"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "hub_platform.identity.password_validation.PasswordComplexityValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Email (env-driven; console backend is the safe local default until SMTP Edevs is wired in E02).
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Edevs Hub <no-reply@edevs.tech>")

# Base URL of the internal UI, used to build links inside transactional emails.
INTERNAL_UI_BASE_URL = os.environ.get("INTERNAL_UI_BASE_URL", "http://localhost:5173")

# Ключ шифрования секретов в БД (Fernet). В production задаётся явно; иначе
# детерминированно выводится из SECRET_KEY (см. hub_platform.identity.crypto).
HUB_FIELD_ENCRYPTION_KEY = os.environ.get("HUB_FIELD_ENCRYPTION_KEY", "")

# Password reset link lifetime. UI обещает 30 минут (default_token_generator uses this setting).
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", str(30 * 60)))

# Транспорт и cookie. По умолчанию безопасно вне DEBUG; локальная разработка и тесты не ломаются.
_secure_default = not DEBUG and not TESTING
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.environ.get("HUB_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
SESSION_COOKIE_SECURE = env_bool("HUB_COOKIE_SECURE", _secure_default)
CSRF_COOKIE_SECURE = env_bool("HUB_COOKIE_SECURE", _secure_default)
SECURE_SSL_REDIRECT = env_bool("HUB_SSL_REDIRECT", _secure_default)
SECURE_HSTS_SECONDS = int(os.environ.get("HUB_HSTS_SECONDS", str(60 * 60 * 24 * 365) if _secure_default else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Лимиты на чувствительные эндпоинты (брутфорс/злоупотребление). В тестах отключены.
_THROTTLE_RATES = {"login": "10/min", "password_reset": "5/min", "totp": "10/min"}
if TESTING:
    _THROTTLE_RATES = {scope: None for scope in _THROTTLE_RATES}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "hub_platform.api.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": _THROTTLE_RATES,
}

CORS_ALLOWED_ORIGINS = env_list(
    "HUB_CORS_ALLOWED_ORIGINS",
    ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s correlation_id=%(correlation_id)s"
        }
    },
    "filters": {
        "correlation_id": {"()": "hub_platform.events.logging.CorrelationIdLogFilter"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "filters": ["correlation_id"],
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
