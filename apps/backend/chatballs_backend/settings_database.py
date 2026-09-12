import os

from django.core.exceptions import ImproperlyConfigured

from chatballs_backend.settings_env import env_bool, env_secret


def _credentials() -> tuple[dict[str, str], dict[str, str]]:
    # Имена ролей — константы продукта, а не настройка установки: их создаёт
    # deploy/postgres/init-runtime-roles.sh при первом старте. Переменные
    # окружения остаются переопределением для нестандартных установок.
    users = {
        "app": os.environ.get("POSTGRES_APP_USER", "chatballs_app"),
        "platform": os.environ.get("POSTGRES_PLATFORM_USER", "chatballs_platform"),
        "migration": os.environ.get(
            "POSTGRES_MIGRATION_USER", "chatballs_migration"
        ),
    }
    # Пароли ролей генерирует первый старт стека в томах с секретами; человек их
    # не вводит и не хранит. Пароли platform и migration лежат в своих томах
    # (подкаталоги platform/ и schema/), которые монтируются только процессам с
    # этими ролями; у остальных файла нет и остаётся default. Переменные
    # окружения остаются переопределением.
    fallback = env_secret("POSTGRES_PASSWORD", "schema/postgres_password", "chatballs")
    passwords = {
        "app": env_secret("POSTGRES_APP_PASSWORD", "postgres_app_password", fallback),
        "platform": env_secret(
            "POSTGRES_PLATFORM_PASSWORD", "platform/postgres_platform_password", fallback
        ),
        "migration": env_secret(
            "POSTGRES_MIGRATION_PASSWORD", "schema/postgres_migration_password", fallback
        ),
    }
    return users, passwords


def _pool_options(*, testing: bool) -> dict | None:
    # ASGI-серверы исполняют ORM в короткоживущих потоках sync_to_async;
    # persistent-соединения (CONN_MAX_AGE > 0) в таких потоках осиротевают и
    # исчерпывают max_connections Postgres. Вместо них — psycopg pool на процесс:
    # соединения возвращаются в пул независимо от потока и ограничены сверху.
    # CHATBALLS_DB_POOL_MAX=0 отключает пул (короткоживущие соединения на запрос).
    if testing:
        return None
    max_size = int(os.environ.get("CHATBALLS_DB_POOL_MAX", "4"))
    if max_size <= 0:
        return None
    return {
        "min_size": int(os.environ.get("CHATBALLS_DB_POOL_MIN", "1")),
        "max_size": max_size,
        "timeout": float(os.environ.get("CHATBALLS_DB_POOL_TIMEOUT", "10")),
    }


def build_databases(*, debug: bool, testing: bool) -> dict[str, dict]:
    role = os.environ.get("CHATBALLS_DB_ROLE", "app").lower()
    if role not in {"app", "platform", "migration"}:
        raise ImproperlyConfigured("CHATBALLS_DB_ROLE must be app, platform or migration")
    users, passwords = _credentials()
    if not debug and not testing and len(set(users.values())) != 3:
        raise ImproperlyConfigured(
            "App, platform and migration database users must be distinct"
        )
    pool = _pool_options(testing=testing)

    def config(selected_role: str) -> dict:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "chatballs"),
            "USER": users[selected_role],
            "PASSWORD": passwords[selected_role],
            "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            # Пул несовместим с persistent-соединениями: с ним CONN_MAX_AGE
            # обязан быть 0, а без пула persistent-режим возвращать нельзя
            # (см. _pool_options).
            "CONN_MAX_AGE": 0,
            "OPTIONS": {"pool": dict(pool)} if pool else {},
        }

    databases = {"default": config("migration" if testing else role)}
    # Алиас platform поднимается только там, где он нужен: в платформенной
    # поверхности и в воркере (CHATBALLS_DB_PLATFORM_ALIAS=1 — он захватывает
    # outbox всех организаций). Остальные процессы пароль этой роли не читают;
    # обращение к алиасу там упадёт сразу, а не откроет обход изоляции.
    if testing or role == "platform" or env_bool("CHATBALLS_DB_PLATFORM_ALIAS"):
        databases["platform"] = config("platform")
    if testing:
        # Тесты создают свою БД и подключаются владельцем кластера. Его пароль
        # приходит оттуда же, откуда у остальных ролей: файл секрета инстанса,
        # переменная окружения — переопределение.
        databases["default"]["USER"] = os.environ.get(
            "POSTGRES_USER", "chatballs_bootstrap"
        )
        databases["default"]["PASSWORD"] = env_secret(
            "POSTGRES_PASSWORD", "schema/postgres_password", "chatballs"
        )
        databases["platform"]["TEST"] = {"MIRROR": "default"}
    return databases
