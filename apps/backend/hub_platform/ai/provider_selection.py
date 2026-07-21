"""Выбор credential-режима и провайдера агента (SPEC-HUB-0027 §9).

Раньше эта функция сохраняла выбор в `Channel.provider_integration` как side
effect сохранения агента. Теперь она ничего не пишет: возвращает разрешённую
интеграцию, а вызывающий сервис ставит её на самого агента — выбор провайдера,
модели и режима credential выполняется в одной форме и одной транзакции, а
инвариант проверяется на одной сущности.
"""

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

from hub_platform.ai.models import CredentialMode
from hub_platform.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    mode: str
    model: str
    integration: Integration | None


def configure_agent_provider(
    *, context: TenantContext, mode: str, integration_id: int | None
) -> ProviderSelection:
    if mode not in CredentialMode.values:
        raise ValidationError({"credentialMode": "Unknown credential mode"})
    if mode == CredentialMode.CUSTOAI:
        # CustoAI не использует секрет организации: связь с интеграцией снимается,
        # иначе BYOK-инвариант проверялся бы по осиротевшему полю.
        return ProviderSelection(mode, settings.CUS_CUSTOAI_MODEL, None)
    # Инвариант BYOK: credential_mode = BYOK ⇒ provider_integration ≠ null.
    if integration_id is None:
        raise ValidationError({"providerIntegrationId": "BYOK integration is required"})
    try:
        integration = Integration.objects.get(
            id=integration_id,
            organization_id=context.organization_id,
            kind=IntegrationKind.LLM_PROVIDER,
            provider__in=[IntegrationProvider.OPENROUTER, IntegrationProvider.CUSTOM],
        )
    except (Integration.DoesNotExist, TypeError, ValueError) as error:
        raise ValidationError(
            {"providerIntegrationId": "Unknown OpenRouter or Custom integration"}
        ) from error
    model = str(integration.config.get("default_model", "")).strip()
    if not model:
        raise ValidationError(
            {"providerIntegrationId": "Integration default model is required"}
        )
    return ProviderSelection(mode, model, integration)
