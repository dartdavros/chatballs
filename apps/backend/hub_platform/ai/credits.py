from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from django.conf import settings

from hub_platform.ai.provider.base import ChatMessage, ChatResult
from hub_platform.subscriptions.errors import (
    EntitlementRequired,
    QuotaExceeded,
    SubscriptionDomainError,
)
from hub_platform.subscriptions.keys import EntitlementKey, QuotaKey
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.subscriptions.reservation_service import (
    commit_usage_reservation,
    release_usage,
    reserve_usage,
)
from hub_platform.tenancy.context import TenantContext

MANAGED_AI_QUOTA_MESSAGE = (
    "Невозможно выполнить запрос из-за достижения лимита Managed AI credits. "
    "Оплатите новый период или подключите BYOK через Custom/OpenRouter интеграцию."
)
MANAGED_AI_RULE_VERSION = "custoai-yandexgpt-tokens-v1"
DEFAULT_MAX_COMPLETION_TOKENS = 4096


class ManagedAiQuotaExceeded(SubscriptionDomainError):
    code = "managed_ai_quota_exceeded"

    def __init__(self) -> None:
        super().__init__(MANAGED_AI_QUOTA_MESSAGE)


@dataclass(frozen=True, slots=True)
class ManagedAiReservation:
    idempotency_key: str
    quantity: int
    params: dict


def _context(channel) -> TenantContext:
    return TenantContext.for_resource(channel.organization)


def _assert_entitlement(*, channel, entitlement: str) -> None:
    try:
        policy = get_effective_policy(_context(channel))
    except Exception as error:
        raise EntitlementRequired(entitlement) from error
    if not policy.has_entitlement(entitlement):
        raise EntitlementRequired(entitlement)


def assert_managed_ai_entitlement(*, channel) -> None:
    _assert_entitlement(channel=channel, entitlement=EntitlementKey.MANAGED_AI)


def assert_byok_ai_entitlement(*, channel) -> None:
    _assert_entitlement(channel=channel, entitlement=EntitlementKey.BYOK_AI)


def _prompt_token_upper_bound(messages: list[ChatMessage]) -> int:
    # A token cannot contain more information than its UTF-8 byte sequence.
    # The per-message allowance covers roles and chat-template separators.
    return 64 + sum(
        len(item.role.encode()) + len(item.content.encode()) + 64
        for item in messages
    )


def reserve_managed_ai_tokens(
    *, channel, messages: list[ChatMessage], params: dict | None
) -> ManagedAiReservation:
    """Reserve a conservative upper token bound before the provider call."""
    key = f"managed-ai:{uuid4()}"
    prompt_upper_bound = _prompt_token_upper_bound(messages)
    bounded_params = dict(params or {})
    requested = bounded_params.get(
        "max_tokens",
        bounded_params.get("max_completion_tokens", DEFAULT_MAX_COMPLETION_TOKENS),
    )
    try:
        requested = int(requested)
    except (TypeError, ValueError):
        requested = DEFAULT_MAX_COMPLETION_TOKENS
    requested = max(1, requested)
    try:
        result = reserve_usage(
            context=_context(channel),
            quota_key=QuotaKey.MANAGED_AI_CREDITS,
            idempotency_key=key,
            lease_seconds=max(
                60,
                int(settings.HUB_AI_REQUEST_TIMEOUT)
                * (int(settings.HUB_AI_MAX_RETRIES) + 1)
                + 120,
            ),
            source="ai.managed_invocation",
            aggregate_type="LlmInvocation",
            quantity=prompt_upper_bound + requested,
            reserve_up_to_available=True,
        )
    except QuotaExceeded as error:
        raise ManagedAiQuotaExceeded() from error

    reserved = result.reservation.quantity
    output_budget = reserved - prompt_upper_bound
    if output_budget <= 0:
        release_usage(context=_context(channel), idempotency_key=key)
        raise ManagedAiQuotaExceeded()

    bounded_params["max_tokens"] = max(1, min(requested, output_budget))
    bounded_params.pop("max_completion_tokens", None)
    return ManagedAiReservation(key, reserved, bounded_params)


def release_managed_ai_tokens(*, channel, reservation: ManagedAiReservation) -> None:
    release_usage(context=_context(channel), idempotency_key=reservation.idempotency_key)


def commit_managed_ai_tokens(
    *, channel, reservation: ManagedAiReservation, result: ChatResult, invocation_id: int
) -> None:
    commit_usage_reservation(
        context=_context(channel),
        idempotency_key=reservation.idempotency_key,
        quantity=result.total_tokens,
        metadata={
            "invocationId": invocation_id,
            "model": result.model,
            "promptTokens": result.prompt_tokens,
            "completionTokens": result.completion_tokens,
            "creditScaleTokens": 1000,
        },
        rule_version=MANAGED_AI_RULE_VERSION,
    )
