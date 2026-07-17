import time

from django.conf import settings

from hub_platform.ai import limits, pricing
from hub_platform.ai.credits import assert_managed_ai_entitlement, consume_invocation_credits
from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus
from hub_platform.ai.pii import redact
from hub_platform.ai.provider import routing
from hub_platform.ai.provider.base import ChatMessage, ChatResult, EmbeddingResult, ProviderError
from hub_platform.ai.provider.factory import get_provider
from hub_platform.ai.provider.resilience import CircuitBreaker, call_with_resilience

_breaker = CircuitBreaker()


def invoke_chat(*, channel, messages: list[ChatMessage], purpose: str, model: str | None = None, params: dict | None = None, used_fragment_ids: list | None = None) -> ChatResult:
    agent = channel.ai_agent
    model = model or agent.model

    # C07: managed_ai entitlement gates platform-managed LLM usage. BYOK paths
    # (track B) will bypass this when the org supplies its own credentials.
    assert_managed_ai_entitlement(channel=channel)

    try:
        limits.assert_within_limits(channel, agent)
    except limits.LimitExceeded as error:
        LlmInvocation.objects.create(
            organization=channel.organization,
            channel=channel, product=channel.product, purpose=purpose, operation="chat", model=model,
            status=LlmInvocationStatus.BLOCKED, error=str(error),
        )
        raise

    # ADR-HUB-0011: отдельное очищенное представление сообщений для LLM.
    safe_messages = [ChatMessage(role=m.role, content=redact(m.content)) for m in messages]
    # BYOK-интеграция канала переопределяет и провайдера, и модель (ADR-HUB-0034 §4,
    # SPEC-HUB-0024 §6): «Модель по умолчанию» интеграции читается в рантайме и
    # заменяет AIAgent.model — устраняет as-built разрыв SPEC-HUB-0005:388.
    provider, model = routing.resolve_provider_and_model(channel, fallback_model=model) \
        if getattr(channel, "provider_integration_id", None) else (get_provider(channel=channel), model)
    started = time.monotonic()
    try:
        result: ChatResult = call_with_resilience(
            lambda: provider.chat(messages=safe_messages, model=model, params=params),
            retries=settings.HUB_AI_MAX_RETRIES,
            breaker=_breaker,
        )
    except ProviderError as error:
        LlmInvocation.objects.create(
            organization=channel.organization,
            channel=channel, product=channel.product, purpose=purpose, operation="chat", model=model,
            status=LlmInvocationStatus.ERROR, error=str(error)[:1000],
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise

    invocation = LlmInvocation.objects.create(
        organization=channel.organization,
        channel=channel, product=channel.product, purpose=purpose, operation="chat", model=result.model,
        prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens, total_tokens=result.total_tokens,
        cost_micros=result.cost_micros or pricing.cost_micros(result.model, result.prompt_tokens, result.completion_tokens),
        latency_ms=int((time.monotonic() - started) * 1000), status=LlmInvocationStatus.SUCCESS,
        used_fragment_ids=used_fragment_ids or [],
    )
    consume_invocation_credits(channel=channel, invocation=invocation)
    return result


def embed_texts(
    *,
    channel=None,
    organization=None,
    texts: list[str],
    model: str,
    purpose: str = "retrieval",
) -> list[EmbeddingResult]:
    # Знания авторские (не клиентские PII), поэтому redaction не требуется.
    provider = get_provider()
    results: list[EmbeddingResult] = call_with_resilience(
        lambda: provider.embed(texts=texts, model=model),
        retries=settings.HUB_AI_MAX_RETRIES,
        breaker=_breaker,
    )
    tokens = sum(result.tokens for result in results)
    LlmInvocation.objects.create(
        organization=channel.organization if channel else organization,
        channel=channel, product=(channel.product if channel else None), purpose=purpose, operation="embedding", model=model,
        prompt_tokens=tokens, total_tokens=tokens, cost_micros=pricing.cost_micros(model, tokens, 0),
        status=LlmInvocationStatus.SUCCESS,
    )
    return results
