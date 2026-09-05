from pathlib import Path


def build_storage_settings(*, base_dir: Path, debug: bool, testing: bool) -> tuple[str, Path, dict[str, dict]]:
    """Хранилище файлов: локальный диск по умолчанию, внешнее S3 — из настроек в
    БД (админ включает в «Настройках»). В .env ничего не задаётся; бэкенды
    динамические и читают текущую конфигурацию инстанса при каждой операции.

    MEDIA_ROOT — каталог локальных файлов (в контейнере это bind-mount data/media).
    """
    media_root = base_dir / "media"
    storages = {
        "default": {"BACKEND": "chatballs.tenancy.storage_backends.DynamicTenantStorage"},
        # Файлы пользователя (фото профиля) — вне тенантного ограждения: пользователь
        # может состоять в нескольких организациях. Ключи под users/<id>/.
        "users": {"BACKEND": "chatballs.tenancy.storage_backends.DynamicUserStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            if testing
            else "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    return "dynamic", media_root, storages
