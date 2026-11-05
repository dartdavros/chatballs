"""Choose a safe recovery action, never infer absence from an ambiguous reply."""

import math
import random

from chatballs.integrations.adapters.contracts import ResultState, RetryStrategy

MAX_ATTEMPTS = 6
TRANSIENT = frozenset({"temporary", "rate_limited", "no_response", "timeout", "network", "connect_failed"})


def backoff(attempt, retry_after=None):
    delay = random.uniform(0.5, 1.0) * min(300, 2 ** min(attempt, 9))
    if isinstance(retry_after, int | float) and math.isfinite(retry_after):
        # Honor multi-day Retry-After values; scheduling does not sleep a worker.
        delay = max(delay, max(0, min(retry_after, 315360000)))
    return delay


def recovery_handler(step, operation):
    if step.retry_strategy == RetryStrategy.SAFE_READ:
        return "execute"
    if step.retry_strategy == RetryStrategy.IDEMPOTENCY_KEY:
        return "execute"
    if step.retry_strategy == RetryStrategy.RECONCILE:
        return "reconcile" if operation.handlers.reconcile else None
    return None


def outcome(step, result):
    if result.state == ResultState.DECISION:
        return "decision"
    if result.state == ResultState.COMPLETED:
        return "completed"
    if result.state == ResultState.PENDING:
        return "pending"
    retryable = result.state == ResultState.UNKNOWN or result.error_code in TRANSIENT
    safe = step.retry_strategy != RetryStrategy.NONE
    if retryable and safe and step.attempt < MAX_ATTEMPTS:
        return "retry"
    # A timed-out write can never become a definitive failure merely because
    # its retry budget ran out, including an idempotency-key write.
    if result.state == ResultState.UNKNOWN:
        return "unknown"
    return "failed"
