"""BYOK provider routing for AI invocations (ADR-HUB-0020:45, ADR-HUB-0034).

Resolves an LLM provider and the effective model from the channel agent's
`provider_integration`. This is the BYOK path: the organization supplies its
own credentials, the integration is selected explicitly on `AIAgent`, and
managed AI credits are not consumed.

Источник провайдера переехал с канала на агента (SPEC-HUB-0027 §9). Один
релиз резолвер падает на `Channel.provider_integration` для записей, не
попавших в data-миграцию; после удаления поля канала fallback уходит.

Selecting the first OpenRouter integration of the org or globally overriding
the owner's choice is forbidden (ADR-HUB-0020:45). The integration MUST be
the one the agent points at.

This module also closes the as-built gap where the OpenRouter «Модель по
умолчанию» field was decorative (SPEC-HUB-0005:388, SPEC-HUB-0024 §4.3, §6):
for OpenRouter and Custom integrations the configured `default_model` is read
at runtime and overrides `AIAgent.model`.
"""

from __future__ import annotations

from hub_platform.ai.provider.base import LLMProvider, ProviderError
from hub_platform.ai.provider.custom import CustomProvider
from hub_platform.ai.provider.demo import DemoProvider
from hub_platform.ai.provider.openrouter import OpenRouterProvider
from hub_platform.integrations.models import Integration, IntegrationProvider


class IntegrationNotConfigured(ProviderError):
    """Raised when a channel has no provider_integration.

    Surfaces a clear configuration error instead of silently falling back to a
    global/first integration (forbidden by ADR-HUB-0020:45). Наследует
    ProviderError: после удаления managed-режима (ADR-HUB-0042 §3) отсутствие
    интеграции — штатное «провайдера нет», а не 500: индексация знаний пишет
    фрагменты без эмбеддингов, ретривер работает лексически.
    """


def resolve_provider(channel) -> LLMProvider:
    """Build the BYOK LLMProvider from the channel's explicit integration."""
    integration = _channel_integration(channel)
    return _provider_from_integration(integration)


def resolve_provider_and_model(channel, *, fallback_model: str) -> tuple[LLMProvider, str]:
    """Build the BYOK provider and the effective model for the channel.

    `fallback_model` is `AIAgent.model`; it is used only when the integration
    has no `default_model` configured, so existing agents keep working while
    the integration-level model field becomes the authoritative override.
    """
    return resolve_provider(channel), resolve_model(channel, fallback_model=fallback_model)


def resolve_model(channel, *, fallback_model: str) -> str:
    integration = _channel_integration(channel)
    return str(integration.config.get("default_model") or "").strip() or fallback_model


def _channel_integration(channel) -> Integration:
    agent = getattr(channel, "ai_agent", None)
    integration = getattr(agent, "provider_integration", None) if agent else None
    if integration is None:
        # Переходный fallback на один релиз (SPEC-HUB-0027 §9 шаг 3): записи,
        # не попавшие в data-миграцию, продолжают работать через канал.
        integration = getattr(channel, "provider_integration", None)
    if integration is None or not integration.secret:
        raise IntegrationNotConfigured(
            "Агент не привязан к LLM-интеграции BYOK; выберите провайдера в настройках агента"
        )
    return integration


def _provider_from_integration(integration: Integration) -> LLMProvider:
    from django.conf import settings

    if integration.provider == IntegrationProvider.OPENROUTER:
        return OpenRouterProvider(
            api_key=integration.secret,
            base_url=integration.config.get("base_url") or settings.CUS_OPENROUTER_BASE_URL,
            timeout=settings.CUS_AI_REQUEST_TIMEOUT,
            proxy_url=integration.config.get("proxy_url", ""),
        )
    if integration.provider == IntegrationProvider.DEMO:
        return DemoProvider()
    if integration.provider == IntegrationProvider.CUSTOM:
        return CustomProvider(
            api_key=integration.secret,
            base_url=integration.config["base_url"],
            timeout=settings.CUS_AI_REQUEST_TIMEOUT,
            proxy_url=integration.config.get("proxy_url", ""),
        )
    raise IntegrationNotConfigured(
        f"Интеграция «{integration.provider}» не является LLM-провайдером BYOK"
    )
