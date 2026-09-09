import os
import sys
from ipaddress import IPv4Address
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from chatballs_backend.settings_database import build_databases
from chatballs_backend.settings_env import env_bool, env_list, env_secret
from chatballs_backend.settings_storage import build_storage_settings

BASE_DIR = Path(__file__).resolve().parent.parent

INSECURE_SECRET_KEY = "local-development-only"

# Автоопределение тестового прогона, чтобы manage.py test / pytest работали
# без ручного выставления production-окружения.
TESTING = "test" in sys.argv or "pytest" in sys.modules
# Ключ подписи не задаётся человеком: его генерирует первый старт стека в том
# с секретами (deploy/secrets). Переменная окружения остаётся как переопределение
# для установок, которые ведут конфигурацию сами.
SECRET_KEY = env_secret("CHATBALLS_SECRET_KEY", "secret_key", INSECURE_SECRET_KEY)
DEBUG = env_bool("CHATBALLS_DEBUG")
# Режим поставки — свойство установки, а не переменной окружения: коробку
# ставят self-hosted, облако выставляет режим явно.
_delivery_mode = os.environ.get("CHATBALLS_DELIVERY_MODE", "").strip().upper()
if not _delivery_mode:
    _delivery_mode = "CLOUD" if (DEBUG or TESTING) else "SELF_HOSTED"
if _delivery_mode not in {"CLOUD", "SELF_HOSTED"}:
    raise ImproperlyConfigured(
        "CHATBALLS_DELIVERY_MODE must be CLOUD or SELF_HOSTED"
    )
CHATBALLS_DELIVERY_MODE = _delivery_mode
ALLOWED_HOSTS = env_list("CHATBALLS_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
if TESTING:
    ALLOWED_HOSTS.extend(["testserver", ".localhost"])
CSRF_TRUSTED_ORIGINS = env_list("CHATBALLS_CSRF_TRUSTED_ORIGINS", [])

# Слабый ключ подписи в production недопустим. При пустом томе секретов это
# означает сломанную установку, а не забытую человеком переменную.
if not DEBUG and not TESTING and SECRET_KEY in {"", INSECURE_SECRET_KEY}:
    raise ImproperlyConfigured(
        "Не удалось прочитать ключ подписи инстанса: том с секретами пуст или "
        "недоступен (deploy/secrets/generate-instance-secrets.sh)"
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "chatballs.identity",
    "chatballs.tenancy",
    "chatballs.platform",
    "chatballs.ai",
    "chatballs.integrations",
    "chatballs.channels",
    "chatballs.conversations",
    "chatballs.notifications",
    "chatballs.webchat",
    "chatballs.health",
    "chatballs.events",
    "chatballs.support_portals",
    "chatballs.calls",
    # django-channels НЕ добавляется в INSTALLED_APPS: его app label «channels»
    # конфликтует с доменным chatballs.channels, а без runserver-оверрайда
    # (сервер — uvicorn) библиотеке достаточно CHANNEL_LAYERS.
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "chatballs.http.middleware.TlsAwareCookieMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "chatballs.http.middleware.ContentSecurityPolicyMiddleware",
    "chatballs.http.middleware.LocalCorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "chatballs.identity.middleware.SessionActivityMiddleware",
    "chatballs.events.middleware.CorrelationIdMiddleware",
    "chatballs.tenancy.middleware.TenantContextMiddleware",
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
# PostgreSQL (SPEC-CHATBALLS-0013 §9). В тестах — InMemory layer.
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

DATABASE_ROUTERS = ["chatballs.tenancy.routing.ForcedAliasRouter"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "chatballs.identity.password_validation.PasswordComplexityValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Email (env-driven; console backend — безопасный локальный дефолт, SMTP задаётся установщиком).
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Chatballs <no-reply@localhost>")

# Base URL of the internal UI, used to build links inside transactional emails.
INTERNAL_UI_BASE_URL = os.environ.get("INTERNAL_UI_BASE_URL", "http://localhost:5173")

# Ключ шифрования секретов в БД (Fernet). Как и остальные секреты инстанса —
# из тома, куда его кладёт первый старт стека; человек его не вводит. Пустое
# значение означает установку, до которой файл ещё не доехал: тогда ключ
# выводится из SECRET_KEY тем же способом (см. chatballs.identity.crypto).
CHATBALLS_FIELD_ENCRYPTION_KEY = env_secret(
    "CHATBALLS_FIELD_ENCRYPTION_KEY", "field_encryption_key", ""
)

# AI provider runtime. The local adapter is explicit and test-only.
CHATBALLS_AI_PROVIDER = os.environ.get("CHATBALLS_AI_PROVIDER", "")
if TESTING and not CHATBALLS_AI_PROVIDER:
    CHATBALLS_AI_PROVIDER = "test"
CHATBALLS_OPENROUTER_BASE_URL = os.environ.get("CHATBALLS_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
CHATBALLS_AI_REQUEST_TIMEOUT = float(os.environ.get("CHATBALLS_AI_REQUEST_TIMEOUT", "30"))
CHATBALLS_AI_MAX_RETRIES = int(os.environ.get("CHATBALLS_AI_MAX_RETRIES", "2"))
CHATBALLS_AI_GLOBAL_DAILY_COST_LIMIT_MICROS = int(
    os.environ.get("CHATBALLS_AI_GLOBAL_DAILY_COST_LIMIT_MICROS", "0")
)  # 0 = без лимита
CHATBALLS_AI_PRICING: dict = {}  # переопределение цен micro-USD/токен по модели
CHATBALLS_AI_EMBEDDING_MODEL = os.environ.get("CHATBALLS_AI_EMBEDDING_MODEL", "openai/text-embedding-3-small")
# Модель расшифровки голосовых (OpenAI-совместимый /audio/transcriptions).

# Managed-провайдер CustoAI удалён (ADR-CHATBALLS-0042 §3): AI — только через
# интеграцию организации (BYOK).

# Long-poll hold-time мессенджеров (сек). Держим малым: единый воркер выполняет
# и inbound-поллинг, и outbox-диспатч в одном потоке — при большом hold-time
# getUpdates/updates блокирует цикл и outbox (приглашения звонков, уведомления,
# ответы AI) уходит с задержкой в размер long-poll на каждое подключение.
CHATBALLS_MESSENGER_POLL_TIMEOUT_SECONDS = int(os.environ.get("CHATBALLS_MESSENGER_POLL_TIMEOUT_SECONDS", "2"))

# Срок жизни анонимной сессии виджета: отсчёт от последней активности, а не от
# выдачи, — посетитель, который переписывается неделями, историю не теряет.
# Токен лежит в localStorage браузера, поэтому бессрочным он быть не должен:
# на общем компьютере он открывал бы чужую переписку сколько угодно долго.
CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS = int(
    os.environ.get("CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS", str(30 * 24 * 60 * 60))
)
if CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS <= 0:
    raise ImproperlyConfigured("CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS must be positive")

# Password reset link lifetime. UI обещает 30 минут (default_token_generator uses this setting).
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", str(30 * 60)))

# Транспорт и cookie.
#
# Коробку ставят одной командой и первый раз открывают по http — по адресу
# сервера, когда домена и сертификата ещё нет. Поэтому жёсткость транспорта
# не включается настройкой «вне DEBUG»: редирект на https делает шлюз, когда
# у него реально есть сертификат, а Secure-cookie и префикс __Host- ставит
# TlsAwareCookieMiddleware по факту TLS у конкретного запроса. Так установка
# работает сразу и ужесточается сама, как только перед ней появляется TLS.
_secure_default = not DEBUG and not TESTING
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.environ.get("CHATBALLS_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
SESSION_COOKIE_SECURE = env_bool("CHATBALLS_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CHATBALLS_COOKIE_SECURE", False)
SECURE_SSL_REDIRECT = env_bool("CHATBALLS_SSL_REDIRECT", False)
# HSTS Django отдаёт только на запросах, пришедших по TLS, поэтому установка
# на голом http его не получает и не «залипает» на несуществующий https.
SECURE_HSTS_SECONDS = int(
    os.environ.get("CHATBALLS_HSTS_SECONDS", str(60 * 60 * 24 * 365) if _secure_default else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Файловые вложения знаний (ADR-CHATBALLS-0023). Файлы отдаются только через
# download-endpoint (FileResponse), прямого статик-роутинга MEDIA нет.
MEDIA_URL = "media/"
CHATBALLS_STORAGE_BACKEND, MEDIA_ROOT, STORAGES = build_storage_settings(
    base_dir=BASE_DIR,
    debug=DEBUG,
    testing=TESTING,
)

# Публичный адрес Hub: абсолютные ссылки, уходящие клиентам (download вложений).
CHATBALLS_PUBLIC_BASE_URL = os.environ.get("CHATBALLS_PUBLIC_BASE_URL", "http://localhost:8000")

# Публичные порталы поддержки размещаются на отдельных хостах.
# Базовый домен порталов помощи задаёт установщик (CHATBALLS_HELP_BASE_DOMAIN);
# по умолчанию — localhost, никаких зашитых доменов.
CHATBALLS_HELP_BASE_DOMAIN = os.environ.get(
    "CHATBALLS_HELP_BASE_DOMAIN",
    "localhost",
).strip().lower().rstrip(".")
CHATBALLS_HELP_PUBLIC_SCHEME = os.environ.get("CHATBALLS_HELP_PUBLIC_SCHEME", "https").strip().lower()
CHATBALLS_HELP_PUBLIC_PORT = os.environ.get("CHATBALLS_HELP_PUBLIC_PORT", "").strip()
# Адрес, на который владелец направляет A-запись домена портала. Штатный
# источник — сам адрес установки (его знает только она сама, см.
# chatballs.support_portals.public_address); переменные ниже остаются
# переопределением для контуров, которые ведут конфигурацию сами. Пустое
# значение — не ошибка установки: до мастера первого запуска адреса просто
# ещё нет, а порталов с доменами тем более.
_configured_help_ipv4 = os.environ.get("CHATBALLS_HELP_PUBLIC_IPV4", "").strip()
if not _configured_help_ipv4:
    _listening_ip = os.environ.get("CHATBALLS_WEB_LISTENING_IP", "").strip()
    if _listening_ip not in {"", "0.0.0.0", "::"}:
        _configured_help_ipv4 = _listening_ip
CHATBALLS_HELP_PUBLIC_IPV4 = _configured_help_ipv4
if CHATBALLS_HELP_PUBLIC_IPV4:
    try:
        IPv4Address(CHATBALLS_HELP_PUBLIC_IPV4)
    except ValueError as error:
        raise ImproperlyConfigured(
            "CHATBALLS_HELP_PUBLIC_IPV4 must be a valid IPv4 address"
        ) from error

# P2P calls: opaque invitation lifetime and short-lived signaling/media access.
CHATBALLS_CALL_INVITE_TTL_SECONDS = int(os.environ.get("CHATBALLS_CALL_INVITE_TTL_SECONDS", str(5 * 60)))
CHATBALLS_CALL_ACCESS_TTL_SECONDS = int(os.environ.get("CHATBALLS_CALL_ACCESS_TTL_SECONDS", str(60 * 60)))
# Grace period: принятый звонок без установленного соединения закрывается FAILED.
CHATBALLS_CALL_CONNECT_GRACE_SECONDS = int(os.environ.get("CHATBALLS_CALL_CONNECT_GRACE_SECONDS", str(2 * 60)))
# Grace period восстановления активного звонка после обрыва участника.
CHATBALLS_CALL_RECONNECT_GRACE_SECONDS = int(os.environ.get("CHATBALLS_CALL_RECONNECT_GRACE_SECONDS", str(60)))
# C07 concurrent quota: lease TTL for a p2p-call slot reservation. A crashed
# session is released by the reservation sweep once the lease lapses.
CHATBALLS_CONCURRENT_CALL_LEASE_SECONDS = int(
    os.environ.get("CHATBALLS_CONCURRENT_CALL_LEASE_SECONDS", str(2 * 60 * 60))
)
if (
    CHATBALLS_CALL_INVITE_TTL_SECONDS <= 0
    or CHATBALLS_CALL_ACCESS_TTL_SECONDS <= 0
    or CHATBALLS_CALL_CONNECT_GRACE_SECONDS <= 0
    or CHATBALLS_CALL_RECONNECT_GRACE_SECONDS <= 0
):
    raise ImproperlyConfigured("HUB call token TTL values must be positive")

# ICE-серверы для WebRTC (SPEC-CHATBALLS-0013 §10): direct-first через STUN, TURN как
# fallback. Формат URL через запятую (stun:host:port / turn:host:3478?transport=udp).
CHATBALLS_CALL_STUN_URLS = env_list("CHATBALLS_CALL_STUN_URLS", [])
# TURN (Coturn, SPEC-CHATBALLS-0013 §11): backend выдаёт краткоживущие REST-credentials
# по общему static-auth-secret. Пусто локально -> только STUN/direct ICE.
# Адреса TURN владелец задаёт в «Настройках» (там же, где адрес установки);
# переменная остаётся переопределением для установок, ведущих конфигурацию сами.
CHATBALLS_CALL_TURN_URLS = env_list("CHATBALLS_CALL_TURN_URLS", [])
# Общий с coturn секрет генерирует первый старт стека — человек его не вводит.
CHATBALLS_CALL_TURN_SECRET = env_secret("CHATBALLS_CALL_TURN_SECRET", "turn_secret", "")
CHATBALLS_CALL_TURN_TTL_SECONDS = int(os.environ.get("CHATBALLS_CALL_TURN_TTL_SECONDS", str(60 * 60)))
if CHATBALLS_CALL_TURN_TTL_SECONDS <= 0:
    raise ImproperlyConfigured("CHATBALLS_CALL_TURN_TTL_SECONDS must be positive")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Лимиты на чувствительные эндпоинты (брутфорс/злоупотребление). В тестах отключены.
_THROTTLE_RATES = {
    "login": "10/min",
    "password_reset": "5/min",
    "totp": "10/min",
    "call_invite": "30/min",
    # Страница звонка поллит состояние по access token — лимит с запасом.
    "call_access": "120/min",
    "help_feedback": "20/hour",
    # Публичный виджет (chatballs.webchat.throttling): аноним заводит сессию,
    # шлёт сообщения и файлы. Первые четыре ставки считаются по адресу клиента,
    # остальные — по токену сессии.
    #
    # По адресу потолки нарочно высокие: за одним адресом мобильного оператора
    # (CGNAT) сидят тысячи посетителей сайта, и жёсткий лимит выключил бы виджет
    # живым людям, а не скрипту. Их дело — потолок на вал, точный счёт ведут
    # ставки по сессии. Виджет тянет config на каждую загрузку страницы и
    # опрашивает ленту раз в 2.5 с (~24 запроса в минуту на сессию).
    "webchat_config": "600/min",
    "webchat_session": "120/hour",
    "webchat_read": "1200/min",
    "webchat_write": "300/min",
    "webchat_session_read": "120/min",
    # Каждое сообщение — ход AI по ключу организации, каждый файл — место в её
    # хранилище. Здесь считается конкретный собеседник, поэтому строго: живой
    # человек в чате не пишет по двадцать реплик в минуту.
    "webchat_session_write": "20/min",
    "webchat_session_upload": "10/min",
}
if TESTING:
    _THROTTLE_RATES = {scope: None for scope in _THROTTLE_RATES}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "chatballs.api.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": _THROTTLE_RATES,
}

CORS_ALLOWED_ORIGINS = env_list(
    "CHATBALLS_CORS_ALLOWED_ORIGINS",
    ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
)

# Конкретное значение задаёт surface settings. Middleware не добавляет header,
# если policy пуста (например, в узком техническом тесте).
CHATBALLS_CONTENT_SECURITY_POLICY = ""

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
        "correlation_id": {"()": "chatballs.events.logging.CorrelationIdLogFilter"}
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
