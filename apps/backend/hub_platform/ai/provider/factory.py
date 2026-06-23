from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from hub_platform.ai.provider.base import LLMProvider
from hub_platform.ai.provider.local import LocalProvider
from hub_platform.ai.provider.openrouter import OpenRouterProvider


def get_provider() -> LLMProvider:
    name = settings.HUB_AI_PROVIDER or ("openrouter" if settings.HUB_OPENROUTER_API_KEY else "test")
    if name == "test":
        # Тестовый адаптер запрещён в production (PLAN §E04).
        if not (settings.DEBUG or getattr(settings, "TESTING", False)):
            raise ImproperlyConfigured("The test AI provider is not allowed when DEBUG is disabled")
        return LocalProvider()
    if name == "openrouter":
        if not settings.HUB_OPENROUTER_API_KEY:
            raise ImproperlyConfigured("HUB_OPENROUTER_API_KEY is required for the OpenRouter provider")
        return OpenRouterProvider(
            api_key=settings.HUB_OPENROUTER_API_KEY,
            base_url=settings.HUB_OPENROUTER_BASE_URL,
            timeout=settings.HUB_AI_REQUEST_TIMEOUT,
        )
    raise ImproperlyConfigured(f"Unknown AI provider: {name}")
