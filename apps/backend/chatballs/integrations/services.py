from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.i18n import t
from chatballs.identity.models import Organization
from chatballs.integrations.checking import test_integration as test_integration
from chatballs.integrations.external_server import apply_external_settings, is_external_server
from chatballs.integrations.models import (
    PROVIDER_KIND,
    Integration,
    IntegrationProvider,
    IntegrationStatus,
)
from chatballs.integrations.operator_routes import (
    UNSET_GROUP,
    new_operator_route,
    update_operator_group,
)
from chatballs.integrations.outbound import (
    HTTP_SCHEMES,
    PROXY_SCHEMES,
    OutboundUrlRejected,
    clean_config_url,
)
from chatballs.integrations.runtime import (
    advance_revision_after_configuration_change,
)
from chatballs.integrations.web_config import normalized_web_config
from chatballs.tenancy.context import TenantContext


@dataclass(frozen=True)
class IntegrationInput:
    provider: str
    name: str
    secret: str | None = None  # None = не менять при update
    config: dict = field(default_factory=dict)
    channel_id: int | None = None  # канал обработки для подключения
    is_active: bool | None = None
    # Настройки внешнего сервера (externalServer); None = не менять при update.
    external: object | None = None
    group_id: object = UNSET_GROUP


def _resolve_channel(
    organization: Organization,
    channel_id: int | None,
    *,
    current_channel_id: int | None = None,
):
    if not channel_id:
        return None
    from chatballs.channels.models import Channel

    try:
        channel = Channel.objects.select_for_update().get(organization=organization, id=channel_id)
    except Channel.DoesNotExist as error:
        raise ValidationError({"channel": t("channels.not_found")}) from error
    if not channel.is_active and channel.id != current_channel_id:
        raise ValidationError({"channel": t("settings.inactive_channel")})
    return channel


def _email_config(config: dict) -> dict:
    """Email-подключение (ADR-CHATBALLS-0035): адрес и хосты IMAP/SMTP обязательны,
    порты/SSL имеют значения по умолчанию, purpose не поддерживается."""
    if str(config.get("purpose", "")).strip():
        raise ValidationError({"config": t("settings.email_not_a_bot")})
    address = str(config.get("email", "")).strip().lower()
    imap_host = str(config.get("imapHost", config.get("imap_host", ""))).strip()
    smtp_host = str(config.get("smtpHost", config.get("smtp_host", ""))).strip()
    if not address or not imap_host or not smtp_host:
        raise ValidationError({"config": t("settings.email_hosts_required")})
    try:
        imap_port = int(config.get("imapPort", config.get("imap_port")) or 993)
        smtp_port = int(config.get("smtpPort", config.get("smtp_port")) or 465)
    except (TypeError, ValueError) as error:
        raise ValidationError({"config": t("settings.ports_numbers")}) from error
    return {
        "email": address,
        "imap_host": imap_host,
        "imap_port": imap_port,
        "imap_ssl": bool(config.get("imapSsl", config.get("imap_ssl", True))),
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_ssl": bool(config.get("smtpSsl", config.get("smtp_ssl", True))),
    }


def _normalized_config(provider: str, config: dict, previous_config: dict | None = None) -> dict:
    if not isinstance(config, dict):
        raise ValidationError({"config": t("api.object_required")})
    if provider == IntegrationProvider.EMAIL:
        return _email_config(config)
    if provider == IntegrationProvider.WEB:
        return normalized_web_config(config, previous_config)
    base_url = str(config.get("baseUrl", config.get("base_url", ""))).strip()
    result: dict[str, str] = {}
    # Схему проверяем на входе: без неё в base_url принимался, например,
    # file:///, и первый же ответ провайдера уводил скачивание в локальный
    # диск. Приватные адреса здесь разрешены намеренно — self-hosted ставит
    # свой Bot API или LLM-сервер рядом (chatballs.integrations.outbound).
    if base_url:
        try:
            result["base_url"] = clean_config_url(base_url, schemes=HTTP_SCHEMES)
        except OutboundUrlRejected as error:
            raise ValidationError({"config": t("settings.base_url_rejected", error=error)}) from error
    proxy_url = str(config.get("proxyUrl", config.get("proxy_url", ""))).strip()
    if proxy_url:
        try:
            result["proxy_url"] = clean_config_url(proxy_url, schemes=PROXY_SCHEMES)
        except OutboundUrlRejected as error:
            raise ValidationError({"config": t("settings.proxy_url_rejected", error=error)}) from error
    # LLM-провайдеры (OpenRouter, Custom) хранят модель по умолчанию свободным текстом.
    # Для OpenRouter поле исторически декоративно; для Custom оно
    # читается в рантайме (ADR-CHATBALLS-0034 §4). Версионирование модели — дорожка ADR-0034.
    if provider in (IntegrationProvider.OPENROUTER, IntegrationProvider.CUSTOM, IntegrationProvider.DEMO):
        default_model = str(config.get("defaultModel", config.get("default_model", ""))).strip()
        if default_model:
            result["default_model"] = default_model
        elif provider == IntegrationProvider.DEMO:
            result["default_model"] = "demo"
        # Модель расшифровки голосовых (POST /audio/transcriptions); пусто — whisper-1.
        transcription_model = str(config.get("transcriptionModel", config.get("transcription_model", ""))).strip()
        if transcription_model:
            result["transcription_model"] = transcription_model
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
            raise ValidationError({"config": t("settings.custom_base_url_required")})
        if "default_model" not in result:
            raise ValidationError({"config": t("settings.custom_model_required")})
    return result


def _publish_web_widget(*, context: TenantContext, integration: Integration) -> None:
    """Web-виджет проверяется локально, без внешнего API, — поэтому проверяем сразу
    после сохранения. Иначе любая правка подключения оставляла бы виджет в DRAFT, а
    подключение в UNCHECKED; раздача требует PUBLISHED + OK (webchat.views), и чат на
    сайте молча падал бы в «Чат временно недоступен» до ручного «Проверить»."""
    from chatballs.webchat.widgets import ensure_widget

    # Отдельным вызовом — чтобы конфликт смены режима остался 400 на сохранении;
    # внутри проверки та же ошибка превратилась бы в статус ERROR.
    ensure_widget(integration)
    test_integration(context=context, integration=integration)


def _validate_provider(provider: str) -> str:
    # Сервисное подключение создаётся только через service_connections: там
    # адаптер, схема настроек и проверка доступа.
    if provider not in IntegrationProvider.values or provider == IntegrationProvider.ADAPTER:
        raise ValidationError({"provider": t("settings.unknown_provider")})
    return provider


@transaction.atomic
def create_integration(*, context: TenantContext, data: IntegrationInput) -> Integration:
    organization = context.organization
    provider = _validate_provider(data.provider)
    name = data.name.strip()
    if not name:
        raise ValidationError({"name": t("settings.name_required")})
    if provider == IntegrationProvider.CUSTOM and not (data.secret or "").strip():
        raise ValidationError({"secret": t("settings.api_key_required")})
    if provider == IntegrationProvider.EMAIL and not (data.secret or "").strip():
        raise ValidationError({"secret": t("settings.mailbox_password_required")})
    integration = Integration(
        organization=organization,
        kind=PROVIDER_KIND[provider],
        provider=provider,
        name=name,
        # У демо-провайдера ключа нет; маркер нужен резолверу (routing требует secret).
        secret=(data.secret or "").strip() or ("demo" if provider == IntegrationProvider.DEMO else ""),
        channel=_resolve_channel(organization, data.channel_id) or new_operator_route(context, data),
        is_active=True if data.is_active is None else data.is_active,
        status=IntegrationStatus.UNCHECKED,
    )
    if is_external_server(provider):
        apply_external_settings(integration, data.external)
    else:
        integration.config = _normalized_config(provider, data.config)
    integration.full_clean(exclude=["secret", "secret_headers"])
    integration.save()
    if integration.provider == IntegrationProvider.WEB:
        _publish_web_widget(context=context, integration=integration)
    return integration

@transaction.atomic
def update_integration(
    *, context: TenantContext, integration: Integration, data: IntegrationInput
) -> Integration:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    if integration.provider == IntegrationProvider.ADAPTER:
        raise ValidationError({"provider": t("settings.unknown_provider")})
    if integration.provider == IntegrationProvider.WEB:
        # Версию согласия считаем по последней сохранённой конфигурации.
        integration = Integration.objects.select_for_update().get(
            pk=integration.pk, organization=context.organization
        )
    previous_config = integration.config
    previous_secret = integration.secret
    if not is_external_server(integration.provider):
        integration.config = _normalized_config(
            integration.provider, data.config, previous_config=previous_config
        )
    elif data.external is not None:
        apply_external_settings(integration, data.external)
    integration.name = data.name.strip() or integration.name
    integration.channel = _resolve_channel(
        integration.organization,
        data.channel_id,
        current_channel_id=integration.channel_id,
    ) or new_operator_route(context, data)
    update_operator_group(context, integration, data.group_id)
    if data.is_active is not None:
        integration.is_active = data.is_active
    # Пустой/отсутствующий секрет при обновлении не затирает существующий.
    if data.secret:
        integration.secret = data.secret.strip()
    advance_revision_after_configuration_change(
        integration,
        previous_config=previous_config,
        previous_secret=previous_secret,
    )
    integration.status = IntegrationStatus.UNCHECKED
    integration.last_checked_at = None
    integration.last_error = ""
    integration.last_error_code = ""
    integration.full_clean(exclude=["secret", "secret_headers"])
    integration.save()
    if integration.provider == IntegrationProvider.WEB:
        _publish_web_widget(context=context, integration=integration)
    if is_external_server(integration.provider):
        # Сервер выключили или запрос перестал быть «только чтение» —
        # агенты такой инструмент больше не вызывают.
        from chatballs.ai.agent_tools import drop_unavailable_tools

        drop_unavailable_tools(integration)
    return integration
