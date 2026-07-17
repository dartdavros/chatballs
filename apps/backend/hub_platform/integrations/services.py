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
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.usage_service import record_usage
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True)
class IntegrationInput:
    provider: str
    name: str
    secret: str | None = None  # None = не менять при update
    config: dict = field(default_factory=dict)
    channel_id: int | None = None  # канал обработки для подключения (ADR-HUB-0019)


def _resolve_channel(organization: Organization, channel_id: int | None):
    if not channel_id:
        return None
    from hub_platform.channels.models import Channel

    try:
        return Channel.objects.get(organization=organization, id=channel_id)
    except Channel.DoesNotExist as error:
        raise ValidationError({"channel": "Channel not found"}) from error


def _normalized_config(provider: str, config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValidationError({"config": "Object required"})
    base_url = str(config.get("baseUrl", config.get("base_url", ""))).strip()
    result: dict[str, str] = {}
    if base_url:
        result["base_url"] = base_url
    proxy_url = str(config.get("proxyUrl", config.get("proxy_url", ""))).strip()
    if proxy_url:
        result["proxy_url"] = proxy_url
    # LLM-провайдеры (OpenRouter, Custom) хранят модель по умолчанию свободным текстом.
    # Для OpenRouter поле исторически декоративно (SPEC-HUB-0005:388); для Custom оно
    # читается в рантайме (ADR-HUB-0034 §4). Версионирование модели — дорожка ADR-0034.
    if provider in (IntegrationProvider.OPENROUTER, IntegrationProvider.CUSTOM):
        default_model = str(config.get("defaultModel", config.get("default_model", ""))).strip()
        if default_model:
            result["default_model"] = default_model
    else:
        # Мессенджер-подключения (MAX/Telegram/Web): идентификатор бота.
        bot_username = str(config.get("botUsername", config.get("bot_username", ""))).strip()
        if bot_username:
            result["bot_username"] = bot_username
        # Сервисный бот уведомлений для сотрудников (не привязан к каналу продаж).
        purpose = str(config.get("purpose", "")).strip()
        if purpose:
            result["purpose"] = purpose
    if provider == IntegrationProvider.CUSTOM:
        if not base_url:
            raise ValidationError({"config": "Custom Base URL is required"})
        if "default_model" not in result:
            raise ValidationError({"config": "Custom model is required"})
    return result


def _validate_provider(provider: str) -> str:
    if provider not in IntegrationProvider.values:
        raise ValidationError({"provider": "Unknown provider"})
    return provider


@transaction.atomic
def create_integration(*, context: TenantContext, data: IntegrationInput) -> Integration:
    organization = context.organization
    provider = _validate_provider(data.provider)
    name = data.name.strip()
    if not name:
        raise ValidationError({"name": "Name required"})
    if provider == IntegrationProvider.CUSTOM and not (data.secret or "").strip():
        raise ValidationError({"secret": "Custom API key is required"})
    integration = Integration(
        organization=organization,
        kind=PROVIDER_KIND[provider],
        provider=provider,
        name=name,
        secret=(data.secret or "").strip(),
        config=_normalized_config(provider, data.config),
        channel=_resolve_channel(organization, data.channel_id),
        status=IntegrationStatus.UNCHECKED,
    )
    integration.full_clean(exclude=["secret"])
    integration.save()
    record_usage(
        context=context,
        quota_key=QuotaKey.CLIENT_CONNECTIONS,
        quantity=1,
        idempotency_key=f"connection:{integration.id}",
        source="integration.created",
        aggregate_type="Integration",
        aggregate_id=str(integration.id),
    )
    return integration


@transaction.atomic
def update_integration(
    *, context: TenantContext, integration: Integration, data: IntegrationInput
) -> Integration:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": "Integration belongs to another organization"})
    integration.name = data.name.strip() or integration.name
    integration.config = _normalized_config(integration.provider, data.config)
    integration.channel = _resolve_channel(integration.organization, data.channel_id)
    # Пустой/отсутствующий секрет при обновлении не затирает существующий.
    if data.secret:
        integration.secret = data.secret.strip()
    integration.status = IntegrationStatus.UNCHECKED
    integration.last_checked_at = None
    integration.last_error = ""
    integration.full_clean(exclude=["secret"])
    integration.save()
    return integration


def delete_integration(*, context: TenantContext, integration: Integration) -> None:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": "Integration belongs to another organization"})
    integration.delete()


_CHECKS = {
    IntegrationProvider.OPENROUTER: checks.check_openrouter,
    IntegrationProvider.CUSTOM: checks.check_custom,
    IntegrationProvider.MAX: checks.check_max,
    IntegrationProvider.TELEGRAM: checks.check_telegram,
}


def _check_web(context: TenantContext, integration: Integration) -> tuple[bool, str, dict]:
    """Web-виджет обслуживается нашим же backend'ом — внешнего API нет.
    Проверяем конфигурацию: привязку к каналу и что именно это подключение
    отдаётся виджету (webchat берёт первое WEB-подключение канала)."""
    if integration.channel_id is None:
        return False, "Подключение не привязано к каналу — виджет не активен", {}
    from hub_platform.webchat.services import web_connection_for_channel

    active = web_connection_for_channel(context, integration.channel.code)
    if active is None or active.id != integration.id:
        return False, "Для этого канала виджет обслуживает другое WEB-подключение", {}
    return True, f"Web-виджет активен · канал «{integration.channel.name}»", {}


def test_integration(*, context: TenantContext, integration: Integration) -> Integration:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": "Integration belongs to another organization"})
    if integration.provider == IntegrationProvider.WEB:
        ok, detail, meta = _check_web(context, integration)
    else:
        check = _CHECKS.get(integration.provider)
        if check is None:
            ok, detail, meta = False, "Проверка для этого типа подключения не поддерживается", {}
        else:
            ok, detail, meta = check(secret=integration.secret, base_url=str(integration.config.get("base_url", "")), proxy_url=str(integration.config.get("proxy_url", "")))
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
