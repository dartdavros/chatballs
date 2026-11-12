"""Умеет ли модель ответов агента вызывать инструменты (SPEC-0023 R-10).

Признак знает провайдер: OpenRouter — по каталогу моделей, свой endpoint — по
проверочному вызову. И то и другое — обращение в сеть, а проверочный вызов ещё
и стоит токенов, поэтому ответ кешируется на пару «интеграция — модель».
Смена настроек интеграции меняет её `runtime_revision`, а с ним и ключ.

Три ответа: True, False и None — «неизвестно»: провайдера нет либо узнать не
удалось. Неизвестное держится в кеше недолго, чтобы сбой связи не запоминался
на сутки и при этом не повторялся на каждое открытие карточки.
"""

from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

from chatballs.ai.models import AIAgent
from chatballs.ai.provider import routing
from chatballs.ai.provider.base import LLMProvider, ProviderError
from chatballs.ai.provider.local import LocalProvider
from chatballs.integrations.models import Integration

logger = logging.getLogger(__name__)

KNOWN_TTL = 24 * 60 * 60
UNKNOWN_TTL = 5 * 60
# Карточка агента ждёт этого ответа: срок короче, чем у хода диалога.
CHECK_TIMEOUT = 10.0

_VALUES = {"yes": True, "no": False, "unknown": None}
_MISSING = object()


def _target(agent: AIAgent) -> tuple[Integration, str] | None:
    """Интеграция и модель ответов агента; None — спрашивать некого."""
    integration = agent.provider_integration
    if integration is None or not integration.secret:
        return None
    model = (agent.model or str(integration.config.get("default_model") or "")).strip()
    return (integration, model) if model else None


def _cache_key(integration: Integration, model: str) -> str:
    digest = hashlib.sha256(model.encode("utf-8")).hexdigest()[:32]
    # Discard pre-Responses negatives: they were measured using the wrong
    # protocol and would otherwise disable tools/skills for another 24 hours.
    return f"ai:tool-support:v2:{integration.id}:{integration.runtime_revision}:{digest}"


def _provider(integration: Integration) -> LLMProvider:
    # Тестовая поверхность подменяет провайдера так же, как в get_provider.
    if settings.CHATBALLS_AI_PROVIDER == "test":
        return LocalProvider()
    return routing.provider_for_integration(integration, timeout=CHECK_TIMEOUT)


def _read(key: str) -> object:
    stored = cache.get(key)
    return _VALUES[stored] if stored in _VALUES else _MISSING


def cached_tool_support(agent: AIAgent) -> bool | None:
    """Признак из кеша, без обращения к провайдеру: для списка агентов."""
    target = _target(agent)
    if target is None:
        return None
    value = _read(_cache_key(*target))
    return None if value is _MISSING else value


def resolve_tool_support(agent: AIAgent) -> bool | None:
    """Признак из кеша, а при промахе — от провайдера: для карточки агента."""
    target = _target(agent)
    if target is None:
        return None
    integration, model = target
    key = _cache_key(integration, model)
    value = _read(key)
    if value is not _MISSING:
        return value
    try:
        supported = _provider(integration).supports_tools(model=model)
    except ProviderError as error:
        logger.warning(
            "Tool support check failed for integration %s: %s", integration.id, error
        )
        cache.set(key, "unknown", UNKNOWN_TTL)
        return None
    cache.set(key, "yes" if supported else "no", KNOWN_TTL)
    return supported
