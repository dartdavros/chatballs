import os

from django.core.exceptions import ImproperlyConfigured


def _credentials() -> tuple[dict[str, str], dict[str, str]]:
    users = {
        "app": os.environ.get(
            "POSTGRES_APP_USER", os.environ.get("POSTGRES_USER", "edevs_hub")
        ),
        "platform": os.environ.get(
            "POSTGRES_PLATFORM_USER", os.environ.get("POSTGRES_USER", "edevs_hub")
        ),
        "migration": os.environ.get(
            "POSTGRES_MIGRATION_USER", os.environ.get("POSTGRES_USER", "edevs_hub")
        ),
    }
    passwords = {
        "app": os.environ.get(
            "POSTGRES_APP_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "edevs_hub")
        ),
        "platform": os.environ.get(
            "POSTGRES_PLATFORM_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "edevs_hub")
        ),
        "migration": os.environ.get(
            "POSTGRES_MIGRATION_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "edevs_hub")
        ),
    }
    return users, passwords


def build_databases(*, debug: bool, testing: bool) -> dict[str, dict]:
    role = os.environ.get("HUB_DB_ROLE", "app").lower()
    if role not in {"app", "platform", "migration"}:
        raise ImproperlyConfigured("HUB_DB_ROLE must be app, platform or migration")
    users, passwords = _credentials()
    if not debug and not testing and len(set(users.values())) != 3:
        raise ImproperlyConfigured(
            "App, platform and migration database users must be distinct"
        )

    def config(selected_role: str) -> dict:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "edevs_hub"),
            "USER": users[selected_role],
            "PASSWORD": passwords[selected_role],
            "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }

    databases = {
        "default": config("migration" if testing else role),
        "platform": config("platform"),
    }
    if testing:
        databases["default"]["USER"] = os.environ.get("POSTGRES_USER", "edevs_hub")
        databases["default"]["PASSWORD"] = os.environ.get(
            "POSTGRES_PASSWORD", "edevs_hub"
        )
        databases["platform"]["TEST"] = {"MIRROR": "default"}
    return databases
