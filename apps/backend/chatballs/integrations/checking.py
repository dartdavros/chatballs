from django.core.exceptions import ValidationError
from django.utils import timezone

from chatballs.i18n import t
from chatballs.integrations import checks
from chatballs.integrations.external_check import check_external_server
from chatballs.integrations.external_server import is_external_server
from chatballs.integrations.models import Integration, IntegrationProvider, IntegrationStatus
from chatballs.integrations.runtime import advance_revision_after_successful_check
from chatballs.tenancy.context import TenantContext

_CHECKS = {
    IntegrationProvider.OPENROUTER: checks.check_openrouter,
    IntegrationProvider.CUSTOM: checks.check_custom,
    IntegrationProvider.DEMO: checks.check_demo,
    IntegrationProvider.MAX: checks.check_max,
    IntegrationProvider.TELEGRAM: checks.check_telegram,
    IntegrationProvider.VK: checks.check_vk,
}


def _check_web(context: TenantContext, integration: Integration) -> tuple[bool, str, dict]:
    """Проверить конфигурацию собственного Web-виджета без внешнего API."""

    if integration.channel_id is None:
        return False, t("integrations.check_web_not_bound"), {}
    from chatballs.webchat.widgets import ensure_widget

    try:
        widget = ensure_widget(integration)
    except ValidationError as error:
        return False, "; ".join(error.messages), {}
    if widget is None:
        return False, t("integrations.check_web_no_config"), {}
    if not widget.allowed_origins:
        return False, t("integrations.check_web_no_origins"), {}
    return True, t("integrations.check_web_active", channel=integration.channel.name), {}


def test_integration(*, context: TenantContext, integration: Integration) -> Integration:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    if integration.provider == IntegrationProvider.ADAPTER:
        # Доступ к сервису проверяет его адаптер: service_connections.services.
        raise ValidationError({"integration": t("integrations.check_unsupported")})
    error_code = ""
    if integration.provider == IntegrationProvider.WEB:
        ok, detail, meta = _check_web(context, integration)
    elif is_external_server(integration.provider):
        ok, detail, error_code = check_external_server(integration)
        meta = {}
    elif integration.provider == IntegrationProvider.EMAIL:
        ok, detail, meta = checks.check_email(
            secret=integration.secret,
            config=integration.config,
        )
    else:
        check = _CHECKS.get(integration.provider)
        if check is None:
            ok, detail, meta = False, t("integrations.check_unsupported"), {}
        else:
            ok, detail, meta = check(
                secret=integration.secret,
                base_url=str(integration.config.get("base_url", "")),
                proxy_url=str(integration.config.get("proxy_url", "")),
            )
    integration.status = IntegrationStatus.OK if ok else IntegrationStatus.ERROR
    integration.last_error = "" if ok else detail
    integration.last_error_code = error_code
    integration.last_checked_at = timezone.now()
    update_fields = ["status", "last_error", "last_error_code", "last_checked_at", "updated_at"]
    if ok and advance_revision_after_successful_check(integration):
        # API и event-workers — разные процессы; ревизия инвалидирует их breaker.
        update_fields.append("runtime_revision")
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
