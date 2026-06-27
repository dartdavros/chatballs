from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from hub_platform.ai.provider.base import LLMProvider
from hub_platform.ai.provider.local import LocalProvider
from hub_platform.ai.provider.openrouter import OpenRouterProvider


def _test_provider() -> LLMProvider:
    # Тестовый адаптер запрещён в production (PLAN §E04).
    if not (settings.DEBUG or getattr(settings, "TESTING", False)):
        raise ImproperlyConfigured("The test AI provider is not allowed when DEBUG is disabled")
    return LocalProvider()


def _openrouter_from_integration() -> OpenRouterProvider | None:
    """Use the OpenRouter integration configured in the UI (ADR-HUB-0020), if any."""
    from hub_platform.integrations.models import Integration, IntegrationProvider

    integration = (
        Integration.objects.filter(provider=IntegrationProvider.OPENROUTER)
        .exclude(secret="")
        .order_by("id")
        .first()
    )
    if integration is None or not integration.secret:
        return None
    return OpenRouterProvider(
        api_key=integration.secret,
        base_url=integration.config.get("base_url") or settings.HUB_OPENROUTER_BASE_URL,
        timeout=settings.HUB_AI_REQUEST_TIMEOUT,
    )


def get_provider() -> LLMProvider:
    explicit = settings.HUB_AI_PROVIDER  # "", "openrouter", "test"
    if explicit == "test":
        return _test_provider()

    # Источник истины — интеграция OpenRouter из UI; env остаётся фолбэком.
    if not getattr(settings, "TESTING", False):
        provider = _openrouter_from_integration()
        if provider is not None:
            return provider

    name = explicit or ("openrouter" if settings.HUB_OPENROUTER_API_KEY else "test")
    if name == "test":
        return _test_provider()
    if name == "openrouter":
        if not settings.HUB_OPENROUTER_API_KEY:
            raise ImproperlyConfigured("HUB_OPENROUTER_API_KEY is required for the OpenRouter provider")
        return OpenRouterProvider(
            api_key=settings.HUB_OPENROUTER_API_KEY,
            base_url=settings.HUB_OPENROUTER_BASE_URL,
            timeout=settings.HUB_AI_REQUEST_TIMEOUT,
        )
    raise ImproperlyConfigured(f"Unknown AI provider: {name}")
