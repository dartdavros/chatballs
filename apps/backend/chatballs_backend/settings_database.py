import os

from django.core.exceptions import ImproperlyConfigured


def _credentials() -> tuple[dict[str, str], dict[str, str]]:
    users = {
        "app": os.environ.get(
            "POSTGRES_APP_USER", os.environ.get("POSTGRES_USER", "chatballs")
        ),
        "platform": os.environ.get(
            "POSTGRES_PLATFORM_USER", os.environ.get("POSTGRES_USER", "chatballs")
        ),
        "migration": os.environ.get(
            "POSTGRES_MIGRATION_USER", os.environ.get("POSTGRES_USER", "chatballs")
        ),
    }
    passwords = {
        "app": os.environ.get(
            "POSTGRES_APP_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "chatballs")
        ),
        "platform": os.environ.get(
            "POSTGRES_PLATFORM_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "chatballs")
        ),
        "migration": os.environ.get(
            "POSTGRES_MIGRATION_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "chatballs")
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

    databases = {
        "default": config("migration" if testing else role),
        "platform": config("platform"),
    }
    if testing:
        databases["default"]["USER"] = os.environ.get("POSTGRES_USER", "chatballs")
        databases["default"]["PASSWORD"] = os.environ.get(
            "POSTGRES_PASSWORD", "chatballs"
        )
        databases["platform"]["TEST"] = {"MIRROR": "default"}
    return databases
