from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chatballs.i18n import t
from chatballs.identity.models import Organization
from chatballs.integrations import checks
from chatballs.integrations.models import (
    PROVIDER_KIND,
    Integration,
    IntegrationProvider,
    IntegrationStatus,
)
from chatballs.integrations.outbound import (
    HTTP_SCHEMES,
    PROXY_SCHEMES,
    OutboundUrlRejected,
    clean_config_url,
)
from chatballs.tenancy.context import TenantContext


@dataclass(frozen=True)
class IntegrationInput:
    provider: str
    name: str
    secret: str | None = None  # None = не менять при update
    config: dict = field(default_factory=dict)
    channel_id: int | None = None  # канал обработки для подключения (ADR-HUB-0019)
    is_active: bool | None = None


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
        channel = Channel.objects.get(organization=organization, id=channel_id)
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


def _normalized_config(provider: str, config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValidationError({"config": t("api.object_required")})
    if provider == IntegrationProvider.EMAIL:
        return _email_config(config)
    if provider == IntegrationProvider.WEB:
        allowed = config.get("allowedOrigins", config.get("allowed_domains", []))
        if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
            raise ValidationError({"config": t("settings.allowed_origins_list")})
        quick_replies = config.get("quickReplies", config.get("quick_replies", []))
        if not isinstance(quick_replies, list) or not all(
            isinstance(item, str) for item in quick_replies
        ):
            raise ValidationError({"config": t("settings.quick_replies_list")})
        return {
            "allowed_domains": [item.strip() for item in allowed if item.strip()],
            "title": str(config.get("title", "")).strip(),
            "accent": str(config.get("accent", "")).strip(),
            "greeting": str(config.get("greeting", "")).strip(),
            "quick_replies": quick_replies,
            "consent_text": str(config.get("consentText", config.get("consent_text", ""))).strip(),
            "consent_version": str(config.get("consentVersion", config.get("consent_version", ""))).strip(),
        }
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
    # Для OpenRouter поле исторически декоративно (SPEC-HUB-0005:388); для Custom оно
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
    if provider not in IntegrationProvider.values:
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
        config=_normalized_config(provider, data.config),
        channel=_resolve_channel(organization, data.channel_id),
        is_active=True if data.is_active is None else data.is_active,
        status=IntegrationStatus.UNCHECKED,
    )
    integration.full_clean(exclude=["secret"])
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
    integration.name = data.name.strip() or integration.name
    integration.config = _normalized_config(integration.provider, data.config)
    integration.channel = _resolve_channel(
        integration.organization,
        data.channel_id,
        current_channel_id=integration.channel_id,
    )
    if data.is_active is not None:
        integration.is_active = data.is_active
    # Пустой/отсутствующий секрет при обновлении не затирает существующий.
    if data.secret:
        integration.secret = data.secret.strip()
    integration.status = IntegrationStatus.UNCHECKED
    integration.last_checked_at = None
    integration.last_error = ""
    integration.full_clean(exclude=["secret"])
    integration.save()
    if integration.provider == IntegrationProvider.WEB:
        _publish_web_widget(context=context, integration=integration)
    return integration


def delete_integration(*, context: TenantContext, integration: Integration) -> None:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    integration.delete()


_CHECKS = {
    IntegrationProvider.OPENROUTER: checks.check_openrouter,
    IntegrationProvider.CUSTOM: checks.check_custom,
    IntegrationProvider.DEMO: checks.check_demo,
    IntegrationProvider.MAX: checks.check_max,
    IntegrationProvider.TELEGRAM: checks.check_telegram,
}


def _check_web(context: TenantContext, integration: Integration) -> tuple[bool, str, dict]:
    """Web-виджет обслуживается нашим же backend'ом — внешнего API нет.
    Проверяем конфигурацию конкретного widget entry point."""
    if integration.channel_id is None:
        return False, t("integrations.check_web_not_bound"), {}
    from chatballs.webchat.widgets import ensure_widget

    try:
        widget = ensure_widget(integration)
    except ValidationError as error:
        return False, "; ".join(error.messages), {}
    if widget is None:
        return False, t("integrations.check_web_no_config"), {}
    # Пустой allowed_origins в проде запрещает вообще все домены (webchat.services.
    # origin_allowed), и на сайте виджет молча показывает «Чат временно недоступен».
    # Проверка обязана падать здесь, а не оставлять зелёный статус при мёртвом чате.
    if not widget.allowed_origins:
        return False, t("integrations.check_web_no_origins"), {}
    return True, t("integrations.check_web_active", channel=integration.channel.name), {}


def test_integration(*, context: TenantContext, integration: Integration) -> Integration:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    if integration.provider == IntegrationProvider.WEB:
        ok, detail, meta = _check_web(context, integration)
    elif integration.provider == IntegrationProvider.EMAIL:
        # Email: сигнатура шире общей (нужен весь config), диспетчеризуется отдельно.
        ok, detail, meta = checks.check_email(secret=integration.secret, config=integration.config)
    else:
        check = _CHECKS.get(integration.provider)
        if check is None:
            ok, detail, meta = False, t("integrations.check_unsupported"), {}
        else:
            ok, detail, meta = check(secret=integration.secret, base_url=str(integration.config.get("base_url", "")), proxy_url=str(integration.config.get("proxy_url", "")))
    integration.status = IntegrationStatus.OK if ok else IntegrationStatus.ERROR
    # Диагностика сохраняется на языке того, кто нажал «Проверить»: она живёт до
    # следующей проверки, и хранить её кодом, как историю диалога, нечего.
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
    if integration.provider == IntegrationProvider.WEB:
        from chatballs.webchat.widgets import sync_widget_check_status

        sync_widget_check_status(integration, ok=ok)
    return integration
