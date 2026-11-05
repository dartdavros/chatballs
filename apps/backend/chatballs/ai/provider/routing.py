"""BYOK provider routing for AI invocations (ADR-CHATBALLS-0020:45, ADR-CHATBALLS-0034).

Resolves an LLM provider and the effective model from the channel agent's
`provider_integration`. This is the BYOK path: the organization supplies its
own credentials, the integration is selected explicitly on `AIAgent`, and
managed AI credits are not consumed.

Источник провайдера переехал с канала на агента. Один
релиз резолвер падает на `Channel.provider_integration` для записей, не
попавших в data-миграцию; после удаления поля канала fallback уходит.

Selecting the first OpenRouter integration of the org or globally overriding
the owner's choice is forbidden (ADR-CHATBALLS-0020:45). The integration MUST be
the one the agent points at.

This module also closes the as-built gap where the OpenRouter «Модель по
умолчанию» field was decorative (SPEC-CHATBALLS-0024 §4.3, §6):
for OpenRouter and Custom integrations the configured `default_model` is read
at runtime and overrides `AIAgent.model`.
"""

from __future__ import annotations

from chatballs.ai.provider.base import LLMProvider, ProviderError
from chatballs.ai.provider.custom import CustomProvider
from chatballs.ai.provider.demo import DemoProvider
from chatballs.ai.provider.openrouter import OpenRouterProvider
from chatballs.i18n import t
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.speech.contracts import Transcriber


class IntegrationNotConfigured(ProviderError):
    """Raised when a channel has no provider_integration.

    Surfaces a clear configuration error instead of silently falling back to a
    global/first integration (forbidden by ADR-CHATBALLS-0020:45). Наследует
    ProviderError: после удаления managed-режима (ADR-CHATBALLS-0042 §3) отсутствие
    интеграции — штатное «провайдера нет», а не 500: индексация знаний пишет
    фрагменты без эмбеддингов, ретривер работает лексически.
    """


def resolve_provider(channel, *, timeout: float | None = None) -> LLMProvider:
    """Build the BYOK LLMProvider from the channel's explicit integration.

    `timeout` переопределяет срок ожидания ответа: интерактивному ходу диалога
    отведено меньше, чем индексации знаний (chatballs.ai.turn).
    """
    integration = _channel_integration(channel)
    return _provider_from_integration(integration, timeout=timeout)


def resolve_provider_and_model(channel, *, fallback_model: str) -> tuple[LLMProvider, str]:
    """Build the BYOK provider and the effective model for the channel.

    `fallback_model` is `AIAgent.model`; it is used only when the integration
    has no `default_model` configured, so existing agents keep working while
    the integration-level model field becomes the authoritative override.
    """
    return resolve_provider(channel), resolve_model(channel, fallback_model=fallback_model)


def resolve_model(channel, *, fallback_model: str) -> str:
    """Модель ответов: выбранная на карточке агента, иначе модель интеграции.

    Порядок именно такой: ключ провайдера один на организацию, а агентов на нём
    несколько, и модель — свойство агента, а не ключа. Пустое поле на карточке
    означает «как у интеграции», поэтому агент, которому модель не назначали,
    продолжает следовать за настройкой провайдера.
    """
    agent = getattr(channel, "ai_agent", None)
    chosen = str(getattr(agent, "model", "") or "").strip()
    if chosen:
        return chosen
    integration = _channel_integration(channel)
    return str(integration.config.get("default_model") or "").strip() or fallback_model


DEFAULT_TRANSCRIPTION_MODEL = "whisper-1"


def resolve_transcription_provider(channel, *, timeout: float | None = None) -> Transcriber:
    """Провайдер расшифровки: отдельная интеграция агента либо провайдер ответов."""
    from chatballs.speech.routing import resolve_transcriber

    return resolve_transcriber(channel, timeout=timeout)


def resolve_transcription_model(channel) -> str:
    """Модель агента → интеграции → default речевого адаптера."""
    from chatballs.speech.routing import resolve_model as resolve_speech_model

    return resolve_speech_model(channel)


def _channel_integration(channel) -> Integration:
    agent = getattr(channel, "ai_agent", None)
    integration = getattr(agent, "provider_integration", None) if agent else None
    if integration is None:
        # Переходный fallback на один релиз: записи,
        # не попавшие в data-миграцию, продолжают работать через канал.
        integration = getattr(channel, "provider_integration", None)
    if integration is None or not integration.secret:
        raise IntegrationNotConfigured(
            t("ai.agent_without_llm_integration")
        )
    return integration


def integration_id(channel) -> int:
    """Идентификатор интеграции канала; 0 — интеграции нет.

    Нужен там, где интеграция — ключ, а не источник настроек: предохранитель
    считает сбои по конкретному ключу организации (chatballs.ai.invocation).
    """
    try:
        return _channel_integration(channel).id
    except IntegrationNotConfigured:
        return 0


def integration_runtime_identity(channel) -> tuple[int, int]:
    """Идентификатор и версия runtime-настроек выбранного провайдера."""

    try:
        integration = _channel_integration(channel)
    except IntegrationNotConfigured:
        return 0, 0
    return integration.id, integration.runtime_revision


def provider_for_integration(
    integration: Integration, *, timeout: float | None = None
) -> LLMProvider:
    """Провайдер конкретной интеграции — там, где канала под рукой нет."""
    return _provider_from_integration(integration, timeout=timeout)


def _provider_from_integration(
    integration: Integration, *, timeout: float | None = None
) -> LLMProvider:
    from django.conf import settings

    wait = timeout or settings.CHATBALLS_AI_REQUEST_TIMEOUT
    if integration.provider == IntegrationProvider.OPENROUTER:
        return OpenRouterProvider(
            api_key=integration.secret,
            base_url=integration.config.get("base_url") or settings.CHATBALLS_OPENROUTER_BASE_URL,
            timeout=wait,
            proxy_url=integration.config.get("proxy_url", ""),
        )
    if integration.provider == IntegrationProvider.DEMO:
        return DemoProvider()
    if integration.provider == IntegrationProvider.CUSTOM:
        return CustomProvider(
            api_key=integration.secret,
            base_url=integration.config["base_url"],
            timeout=wait,
            proxy_url=integration.config.get("proxy_url", ""),
        )
    raise IntegrationNotConfigured(
        t("ai.integration_is_not_llm", provider=integration.provider)
    )
