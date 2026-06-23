import time

from django.conf import settings

from hub_platform.ai import limits, pricing
from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus
from hub_platform.ai.pii import redact
from hub_platform.ai.provider.base import ChatMessage, ChatResult, EmbeddingResult, ProviderError
from hub_platform.ai.provider.factory import get_provider
from hub_platform.ai.provider.resilience import CircuitBreaker, call_with_resilience

_breaker = CircuitBreaker()


def invoke_chat(*, product, messages: list[ChatMessage], purpose: str, release=None, model: str | None = None, params: dict | None = None) -> ChatResult:
    agent = product.ai_agent
    model = model or agent.model

    try:
        limits.assert_within_limits(product, agent)
    except limits.LimitExceeded as error:
        LlmInvocation.objects.create(
            product=product, release=release, purpose=purpose, operation="chat", model=model,
            status=LlmInvocationStatus.BLOCKED, error=str(error),
        )
        raise

    # ADR-HUB-0011: отдельное очищенное представление сообщений для LLM.
    safe_messages = [ChatMessage(role=m.role, content=redact(m.content)) for m in messages]
    provider = get_provider()
    started = time.monotonic()
    try:
        result: ChatResult = call_with_resilience(
            lambda: provider.chat(messages=safe_messages, model=model, params=params),
            retries=settings.HUB_AI_MAX_RETRIES,
            breaker=_breaker,
        )
    except ProviderError as error:
        LlmInvocation.objects.create(
            product=product, release=release, purpose=purpose, operation="chat", model=model,
            status=LlmInvocationStatus.ERROR, error=str(error)[:1000],
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise

    LlmInvocation.objects.create(
        product=product, release=release, purpose=purpose, operation="chat", model=result.model,
        prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens, total_tokens=result.total_tokens,
        cost_micros=pricing.cost_micros(result.model, result.prompt_tokens, result.completion_tokens),
        latency_ms=int((time.monotonic() - started) * 1000), status=LlmInvocationStatus.SUCCESS,
    )
    return result


def embed_texts(*, product, texts: list[str], model: str, purpose: str = "retrieval") -> list[EmbeddingResult]:
    # Знания авторские (не клиентские PII), поэтому redaction не требуется.
    provider = get_provider()
    results: list[EmbeddingResult] = call_with_resilience(
        lambda: provider.embed(texts=texts, model=model),
        retries=settings.HUB_AI_MAX_RETRIES,
        breaker=_breaker,
    )
    tokens = sum(result.tokens for result in results)
    LlmInvocation.objects.create(
        product=product, purpose=purpose, operation="embedding", model=model,
        prompt_tokens=tokens, total_tokens=tokens, cost_micros=pricing.cost_micros(model, tokens, 0),
        status=LlmInvocationStatus.SUCCESS,
    )
    return results
