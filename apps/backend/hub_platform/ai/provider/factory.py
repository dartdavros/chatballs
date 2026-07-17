from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from hub_platform.ai.models import CredentialMode
from hub_platform.ai.provider import routing
from hub_platform.ai.provider.base import LLMProvider, ProviderError
from hub_platform.ai.provider.custoai import CustoAIProvider
from hub_platform.ai.provider.local import LocalProvider


def _test_provider() -> LLMProvider:
    if not (settings.DEBUG or getattr(settings, "TESTING", False)):
        raise ImproperlyConfigured("The test AI provider is not allowed when DEBUG is disabled")
    return LocalProvider()


def _custoai_provider() -> CustoAIProvider:
    if not settings.CUS_CUSTOAI_API_KEY:
        raise ProviderError("CUS_CUSTOAI_API_KEY is required for CustoAI")
    if not settings.CUS_CUSTOAI_MODEL:
        raise ProviderError("CUS_CUSTOAI_MODEL is required for CustoAI")
    return CustoAIProvider(
        api_key=settings.CUS_CUSTOAI_API_KEY,
        base_url=settings.CUS_CUSTOAI_BASE_URL,
        model=settings.CUS_CUSTOAI_MODEL,
        timeout=settings.CUS_AI_REQUEST_TIMEOUT,
    )


def get_provider(*, channel=None) -> LLMProvider:
    """Resolve exactly one explicitly selected credential mode.

    The test adapter is an explicit test-surface override. Production Managed
    requests always use CustoAI's platform credential; BYOK requests always use
    the integration linked to the channel. There is no fallback between modes.
    """
    if settings.CUS_AI_PROVIDER == "test":
        return _test_provider()

    if channel is None:
        return _custoai_provider()

    mode = channel.ai_agent.credential_mode
    if mode == CredentialMode.CUSTOAI:
        return _custoai_provider()
    if mode == CredentialMode.BYOK:
        return routing.resolve_provider(channel)
    raise ProviderError(f"Unknown AI credential mode: {mode}")
