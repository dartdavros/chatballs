"""Выбор LLM-провайдера агента (SPEC-HUB-0027 §9, ADR-CHATBALLS-0042 §3).

Managed-режим CustoAI удалён вместе с тарифным контуром: агент работает только
через интеграцию организации (BYOK, ADR-CHATBALLS-0034). Функция ничего не пишет:
возвращает разрешённую интеграцию и модель, вызывающий сервис ставит их на
агента в одной транзакции. Агент без интеграции — валидное состояние черновика;
активация без провайдера запрещена в set_agent_active.
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from chatballs.tenancy.context import TenantContext


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    model: str
    integration: Integration | None


def configure_agent_provider(
    *, context: TenantContext, integration_id: int | None
) -> ProviderSelection:
    if integration_id is None:
        return ProviderSelection("", None)
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
    return ProviderSelection(model, integration)
