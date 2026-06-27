from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.identity.models import Organization
from hub_platform.integrations import checks
from hub_platform.integrations.models import (
    PROVIDER_KIND,
    Integration,
    IntegrationProvider,
    IntegrationStatus,
)


@dataclass(frozen=True)
class IntegrationInput:
    provider: str
    name: str
    secret: str | None = None  # None = не менять при update
    config: dict = field(default_factory=dict)


def _normalized_config(provider: str, config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValidationError({"config": "Object required"})
    base_url = str(config.get("baseUrl", config.get("base_url", ""))).strip()
    result: dict[str, str] = {}
    if base_url:
        result["base_url"] = base_url
    if provider == IntegrationProvider.OPENROUTER:
        default_model = str(config.get("defaultModel", config.get("default_model", ""))).strip()
        if default_model:
            result["default_model"] = default_model
    else:
        # Мессенджер-подключения (MAX/Telegram/Web): идентификатор бота.
        bot_username = str(config.get("botUsername", config.get("bot_username", ""))).strip()
        if bot_username:
            result["bot_username"] = bot_username
    return result


def _validate_provider(provider: str) -> str:
    if provider not in IntegrationProvider.values:
        raise ValidationError({"provider": "Unknown provider"})
    return provider


@transaction.atomic
def create_integration(*, organization: Organization, data: IntegrationInput) -> Integration:
    provider = _validate_provider(data.provider)
    name = data.name.strip()
    if not name:
        raise ValidationError({"name": "Name required"})
    integration = Integration(
        organization=organization,
        kind=PROVIDER_KIND[provider],
        provider=provider,
        name=name,
        secret=(data.secret or "").strip(),
        config=_normalized_config(provider, data.config),
        status=IntegrationStatus.UNCHECKED,
    )
    integration.full_clean(exclude=["secret"])
    integration.save()
    return integration


@transaction.atomic
def update_integration(*, integration: Integration, data: IntegrationInput) -> Integration:
    integration.name = data.name.strip() or integration.name
    integration.config = _normalized_config(integration.provider, data.config)
    # Пустой/отсутствующий секрет при обновлении не затирает существующий.
    if data.secret:
        integration.secret = data.secret.strip()
    integration.status = IntegrationStatus.UNCHECKED
    integration.last_checked_at = None
    integration.last_error = ""
    integration.full_clean(exclude=["secret"])
    integration.save()
    return integration


def delete_integration(*, integration: Integration) -> None:
    integration.delete()


_CHECKS = {
    IntegrationProvider.OPENROUTER: checks.check_openrouter,
    IntegrationProvider.MAX: checks.check_max,
    IntegrationProvider.TELEGRAM: checks.check_telegram,
}


def test_integration(*, integration: Integration) -> Integration:
    check = _CHECKS.get(integration.provider)
    if check is None:
        ok, detail, meta = False, "Проверка для этого типа подключения не поддерживается", {}
    else:
        ok, detail, meta = check(secret=integration.secret, base_url=str(integration.config.get("base_url", "")))
    integration.status = IntegrationStatus.OK if ok else IntegrationStatus.ERROR
    integration.last_error = "" if ok else detail
    integration.last_checked_at = timezone.now()
    update_fields = ["status", "last_error", "last_checked_at", "updated_at"]
    # Идентичность бота (id/username/имя) — из ответа API, авторитетный источник.
    if ok and meta:
        config = {**integration.config}
        for key in ("bot_id", "bot_username", "bot_name"):
            if meta.get(key):
                config[key] = meta[key]
        if config != integration.config:
            integration.config = config
            update_fields.append("config")
    integration.save(update_fields=update_fields)
    return integration
