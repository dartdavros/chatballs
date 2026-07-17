import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from hub_backend.settings_database import build_databases
from hub_backend.settings_env import env_bool, env_list
from hub_backend.settings_storage import build_storage_settings

BASE_DIR = Path(__file__).resolve().parent.parent

INSECURE_SECRET_KEY = "local-development-only"

# Автоопределение тестового прогона, чтобы manage.py test / pytest работали
# без ручного выставления production-окружения.
TESTING = "test" in sys.argv or "pytest" in sys.modules
SECRET_KEY = os.environ.get("HUB_SECRET_KEY", INSECURE_SECRET_KEY)
DEBUG = env_bool("HUB_DEBUG")
ALLOWED_HOSTS = env_list("HUB_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list("HUB_CSRF_TRUSTED_ORIGINS", [])

# Запрещаем запуск в production с дефолтным/пустым ключом подписи.
if not DEBUG and not TESTING and SECRET_KEY in {"", INSECURE_SECRET_KEY}:
    raise ImproperlyConfigured(
        "HUB_SECRET_KEY must be set to a strong value when HUB_DEBUG is disabled"
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "hub_platform.identity",
    "hub_platform.tenancy",
    "hub_platform.subscriptions",
    "hub_platform.platform",
    "hub_platform.products",
    "hub_platform.ai",
    "hub_platform.integrations",
    "hub_platform.channels",
    "hub_platform.conversations",
    "hub_platform.orders",
    "hub_platform.sales",
    "hub_platform.notifications",
    "hub_platform.webchat",
    "hub_platform.health",
    "hub_platform.events",
    "hub_platform.support",
    "hub_platform.calls",
    # django-channels НЕ добавляется в INSTALLED_APPS: его app label «channels»
    # конфликтует с доменным hub_platform.channels, а без runserver-оверрайда
    # (сервер — uvicorn) библиотеке достаточно CHANNEL_LAYERS.
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "hub_platform.http.middleware.ContentSecurityPolicyMiddleware",
    "hub_platform.http.middleware.LocalCorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "hub_platform.events.middleware.CorrelationIdMiddleware",
    "hub_platform.tenancy.middleware.TenantContextMiddleware",
]

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

AUTH_USER_MODEL = "identity.HumanUser"

# Tests use the disposable cluster owner to create/drop the test database. The
# dedicated RLS suite explicitly SET ROLEs into the non-owner runtime roles.
DATABASES = build_databases(debug=DEBUG, testing=TESTING)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    }
}

# Signaling звонков: Redis только fan-out/presence, source of truth lifecycle —
# PostgreSQL (SPEC-HUB-0013 §9). В тестах — InMemory layer.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
    if TESTING
    else {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [os.environ.get("REDIS_URL", "redis://redis:6379/0")]},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
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
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "CustoCRM <no-reply@edevs.tech>")

# Base URL of the internal UI, used to build links inside transactional emails.
INTERNAL_UI_BASE_URL = os.environ.get("INTERNAL_UI_BASE_URL", "http://localhost:5173")

# Ключ шифрования секретов в БД (Fernet). В production задаётся явно; иначе
# детерминированно выводится из SECRET_KEY (см. hub_platform.identity.crypto).
HUB_FIELD_ENCRYPTION_KEY = os.environ.get("HUB_FIELD_ENCRYPTION_KEY", "")

# AI provider runtime. The local adapter is explicit and test-only.
HUB_AI_PROVIDER = os.environ.get("HUB_AI_PROVIDER", "")
if TESTING and not HUB_AI_PROVIDER:
    HUB_AI_PROVIDER = "test"
HUB_OPENROUTER_BASE_URL = os.environ.get("HUB_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
HUB_AI_REQUEST_TIMEOUT = float(os.environ.get("HUB_AI_REQUEST_TIMEOUT", "30"))
HUB_AI_MAX_RETRIES = int(os.environ.get("HUB_AI_MAX_RETRIES", "2"))
HUB_AI_GLOBAL_DAILY_COST_LIMIT_MICROS = int(
    os.environ.get("HUB_AI_GLOBAL_DAILY_COST_LIMIT_MICROS", "0")
)  # 0 = без лимита
HUB_AI_PRICING: dict = {}  # переопределение цен micro-USD/токен по модели
HUB_AI_EMBEDDING_MODEL = os.environ.get("HUB_AI_EMBEDDING_MODEL", "openai/text-embedding-3-small")

# CustoAI platform credential is configured only through environment/secret storage.
HUB_CUSTOAI_API_KEY = os.environ.get("HUB_CUSTOAI_API_KEY", "")
HUB_CUSTOAI_BASE_URL = os.environ.get("HUB_CUSTOAI_BASE_URL", "https://ai.api.cloud.yandex.net/v1")
HUB_CUSTOAI_MODEL = os.environ.get(
    "HUB_CUSTOAI_MODEL",
    "gpt://b1g89tr9t8iedhnl8pgg/yandexgpt-5.1/latest",
)

# Long-poll hold-time мессенджеров (сек). Держим малым: единый воркер выполняет
# и inbound-поллинг, и outbox-диспатч в одном потоке — при большом hold-time
# getUpdates/updates блокирует цикл и outbox (приглашения звонков, уведомления,
# ответы AI) уходит с задержкой в размер long-poll на каждое подключение.
HUB_MESSENGER_POLL_TIMEOUT_SECONDS = int(os.environ.get("HUB_MESSENGER_POLL_TIMEOUT_SECONDS", "2"))

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
SECURE_HSTS_SECONDS = int(
    os.environ.get("HUB_HSTS_SECONDS", str(60 * 60 * 24 * 365) if _secure_default else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Файловые вложения знаний (ADR-HUB-0023). Файлы отдаются только через
# download-endpoint (FileResponse), прямого статик-роутинга MEDIA нет.
MEDIA_URL = "media/"
HUB_STORAGE_BACKEND, MEDIA_ROOT, STORAGES = build_storage_settings(
    base_dir=BASE_DIR,
    debug=DEBUG,
    testing=TESTING,
)

# Публичный адрес Hub: абсолютные ссылки, уходящие клиентам (download вложений).
HUB_PUBLIC_BASE_URL = os.environ.get("HUB_PUBLIC_BASE_URL", "http://localhost:8000")

# P2P calls: opaque invitation lifetime and short-lived signaling/media access.
HUB_CALL_INVITE_TTL_SECONDS = int(os.environ.get("HUB_CALL_INVITE_TTL_SECONDS", str(5 * 60)))
HUB_CALL_ACCESS_TTL_SECONDS = int(os.environ.get("HUB_CALL_ACCESS_TTL_SECONDS", str(60 * 60)))
# Grace period: принятый звонок без установленного соединения закрывается FAILED.
HUB_CALL_CONNECT_GRACE_SECONDS = int(os.environ.get("HUB_CALL_CONNECT_GRACE_SECONDS", str(2 * 60)))
# Grace period восстановления активного звонка после обрыва участника.
HUB_CALL_RECONNECT_GRACE_SECONDS = int(os.environ.get("HUB_CALL_RECONNECT_GRACE_SECONDS", str(60)))
# C07 concurrent quota: lease TTL for a p2p-call slot reservation. A crashed
# session is released by the reservation sweep once the lease lapses.
HUB_CONCURRENT_CALL_LEASE_SECONDS = int(
    os.environ.get("HUB_CONCURRENT_CALL_LEASE_SECONDS", str(2 * 60 * 60))
)
if (
    HUB_CALL_INVITE_TTL_SECONDS <= 0
    or HUB_CALL_ACCESS_TTL_SECONDS <= 0
    or HUB_CALL_CONNECT_GRACE_SECONDS <= 0
    or HUB_CALL_RECONNECT_GRACE_SECONDS <= 0
):
    raise ImproperlyConfigured("HUB call token TTL values must be positive")

# ICE-серверы для WebRTC (SPEC-HUB-0013 §10): direct-first через STUN, TURN как
# fallback. Формат URL через запятую (stun:host:port / turn:host:3478?transport=udp).
HUB_CALL_STUN_URLS = env_list("HUB_CALL_STUN_URLS", [])
# TURN (Coturn, SPEC-HUB-0013 §11): backend выдаёт краткоживущие REST-credentials
# по общему static-auth-secret. Пусто локально -> только STUN/direct ICE.
HUB_CALL_TURN_URLS = env_list("HUB_CALL_TURN_URLS", [])
HUB_CALL_TURN_SECRET = os.environ.get("HUB_CALL_TURN_SECRET", "")
HUB_CALL_TURN_TTL_SECONDS = int(os.environ.get("HUB_CALL_TURN_TTL_SECONDS", str(60 * 60)))
if HUB_CALL_TURN_TTL_SECONDS <= 0:
    raise ImproperlyConfigured("HUB_CALL_TURN_TTL_SECONDS must be positive")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Лимиты на чувствительные эндпоинты (брутфорс/злоупотребление). В тестах отключены.
_THROTTLE_RATES = {
    "login": "10/min",
    "password_reset": "5/min",
    "totp": "10/min",
    "call_invite": "30/min",
    # Страница звонка поллит состояние по access token — лимит с запасом.
    "call_access": "120/min",
}
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

# Конкретное значение задаёт surface settings. Middleware не добавляет header,
# если policy пуста (например, в узком техническом тесте).
HUB_CONTENT_SECURITY_POLICY = ""

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s %(message)s "
                "correlation_id=%(correlation_id)s"
            )
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
