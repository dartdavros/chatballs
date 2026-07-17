import time

from django.conf import settings

from hub_platform.ai import limits, pricing
from hub_platform.ai.credits import (
    ManagedAiQuotaExceeded,
    assert_byok_ai_entitlement,
    assert_managed_ai_entitlement,
    commit_managed_ai_tokens,
    release_managed_ai_tokens,
    reserve_managed_ai_tokens,
)
from hub_platform.ai.models import CredentialMode, LlmInvocation, LlmInvocationStatus
from hub_platform.ai.pii import redact
from hub_platform.ai.provider import routing
from hub_platform.ai.provider.base import (
    ChatMessage,
    ChatResult,
    EmbeddingResult,
    LLMProvider,
    ProviderError,
)
from hub_platform.ai.provider.factory import get_provider
from hub_platform.ai.provider.resilience import CircuitBreaker, call_with_resilience

_breaker = CircuitBreaker()


def _record_blocked(*, channel, purpose: str, model: str, error: Exception) -> None:
    LlmInvocation.objects.create(
        organization=channel.organization,
        channel=channel,
        product=channel.product,
        purpose=purpose,
        operation="chat",
        model=model,
        status=LlmInvocationStatus.BLOCKED,
        error=str(error),
    )


def _prepare_invocation(*, channel, requested_model: str | None) -> tuple[LLMProvider, str]:
    agent = channel.ai_agent
    mode = agent.credential_mode
    effective_model = agent.model
    if mode == CredentialMode.CUSTOAI:
        assert_managed_ai_entitlement(channel=channel)
        effective_model = settings.HUB_CUSTOAI_MODEL
    elif mode == CredentialMode.BYOK:
        assert_byok_ai_entitlement(channel=channel)
        effective_model = routing.resolve_model(channel, fallback_model=agent.model)
    else:
        raise ValueError(f"Unknown AI credential mode: {mode}")
    selected_model = (
        effective_model
        if mode == CredentialMode.CUSTOAI
        else requested_model or effective_model
    )
    return get_provider(channel=channel), selected_model


def invoke_chat(
    *,
    channel,
    messages: list[ChatMessage],
    purpose: str,
    model: str | None = None,
    params: dict | None = None,
    used_fragment_ids: list | None = None,
) -> ChatResult:
    fallback_model = (
        settings.HUB_CUSTOAI_MODEL
        if channel.ai_agent.credential_mode == CredentialMode.CUSTOAI
        else model or channel.ai_agent.model
    )
    try:
        provider, model = _prepare_invocation(channel=channel, requested_model=model)
        limits.assert_within_limits(channel, channel.ai_agent)
    except (ManagedAiQuotaExceeded, limits.LimitExceeded) as error:
        _record_blocked(
            channel=channel,
            purpose=purpose,
            model=fallback_model,
            error=error,
        )
        raise

    safe_messages = [ChatMessage(role=item.role, content=redact(item.content)) for item in messages]
    reservation = None
    effective_params = params
    if channel.ai_agent.credential_mode == CredentialMode.CUSTOAI:
        try:
            reservation = reserve_managed_ai_tokens(
                channel=channel, messages=safe_messages, params=params
            )
            effective_params = reservation.params
        except ManagedAiQuotaExceeded as error:
            _record_blocked(channel=channel, purpose=purpose, model=model, error=error)
            raise
    started = time.monotonic()
    try:
        result: ChatResult = call_with_resilience(
            lambda: provider.chat(messages=safe_messages, model=model, params=effective_params),
            retries=settings.HUB_AI_MAX_RETRIES,
            breaker=_breaker,
        )
    except ProviderError as error:
        if reservation is not None:
            release_managed_ai_tokens(channel=channel, reservation=reservation)
        LlmInvocation.objects.create(
            organization=channel.organization,
            channel=channel,
            product=channel.product,
            purpose=purpose,
            operation="chat",
            model=model,
            status=LlmInvocationStatus.ERROR,
            error=str(error)[:1000],
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        raise

    invocation = LlmInvocation.objects.create(
        organization=channel.organization,
        channel=channel,
        product=channel.product,
        purpose=purpose,
        operation="chat",
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        cost_micros=result.cost_micros
        or pricing.cost_micros(result.model, result.prompt_tokens, result.completion_tokens),
        latency_ms=int((time.monotonic() - started) * 1000),
        status=LlmInvocationStatus.SUCCESS,
        used_fragment_ids=used_fragment_ids or [],
    )
    if reservation is not None:
        commit_managed_ai_tokens(
            channel=channel,
            reservation=reservation,
            result=result,
            invocation_id=invocation.id,
        )
    return result


def embed_texts(
    *,
    channel=None,
    organization=None,
    texts: list[str],
    model: str,
    purpose: str = "retrieval",
) -> list[EmbeddingResult]:
    provider = get_provider(channel=channel)
    results: list[EmbeddingResult] = call_with_resilience(
        lambda: provider.embed(texts=texts, model=model),
        retries=settings.HUB_AI_MAX_RETRIES,
        breaker=_breaker,
    )
    tokens = sum(result.tokens for result in results)
    LlmInvocation.objects.create(
        organization=channel.organization if channel else organization,
        channel=channel,
        product=(channel.product if channel else None),
        purpose=purpose,
        operation="embedding",
        model=model,
        prompt_tokens=tokens,
        total_tokens=tokens,
        cost_micros=pricing.cost_micros(model, tokens, 0),
        status=LlmInvocationStatus.SUCCESS,
    )
    return results
