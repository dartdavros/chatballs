from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from chatballs.ai.provider import routing
from chatballs.ai.provider.base import LLMProvider, ProviderError
from chatballs.ai.provider.local import LocalProvider
from chatballs.i18n import t
from chatballs.speech.contracts import Transcriber


def _test_provider() -> LLMProvider:
    if not (settings.DEBUG or getattr(settings, "TESTING", False)):
        raise ImproperlyConfigured("The test AI provider is not allowed when DEBUG is disabled")
    return LocalProvider()


def get_provider(*, channel=None, timeout: float | None = None) -> LLMProvider:
    """Resolve the organization's own provider (BYOK, ADR-CHATBALLS-0042 §3).

    The test adapter is an explicit test-surface override. Managed platform
    credentials were removed with the billing domain: every invocation uses the
    integration the agent points at; a call without a channel has no provider
    to resolve and fails cleanly (callers treat ProviderError as "no embeddings",
    lexical search keeps working).
    """
    if settings.CHATBALLS_AI_PROVIDER == "test":
        return _test_provider()

    if channel is None:
        raise ProviderError(
            t("ai.provider_not_configured")
        )
    return routing.resolve_provider(channel, timeout=timeout)


def get_transcription_provider(*, channel=None, timeout: float | None = None) -> Transcriber:
    """Провайдер расшифровки голосовых.

    Отличается от `get_provider` одним: агент может расшифровывать другим
    провайдером, чем отвечает (chatballs.ai.provider.routing).
    """
    if settings.CHATBALLS_AI_PROVIDER == "test":
        return _test_provider()
    if channel is None:
        raise ProviderError(t("ai.provider_not_configured"))
    return routing.resolve_transcription_provider(channel, timeout=timeout)
