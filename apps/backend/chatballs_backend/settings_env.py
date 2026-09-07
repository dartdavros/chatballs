import os
from pathlib import Path

# Секреты инстанса генерируются при первом старте и лежат файлами в томе
# (deploy/secrets/generate-instance-secrets.sh). В .env их нет — установка не
# требует от человека ни одной переменной.
SECRETS_DIR = Path(os.environ.get("CHATBALLS_SECRETS_DIR", "/run/chatballs/secrets"))


def env_secret(name: str, secret_file: str, default: str = "") -> str:
    """Значение из переменной окружения, иначе из файла секрета, иначе default.

    Переменная окружения имеет приоритет: так существующие установки с .env
    продолжают работать без изменений.
    """
    value = os.environ.get(name)
    if value:
        return value
    path_override = os.environ.get(f"{name}_FILE")
    path = Path(path_override) if path_override else SECRETS_DIR / secret_file
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError:
        return default
    return content or default




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
