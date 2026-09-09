import time
from collections.abc import Callable

from chatballs.ai.provider.base import ProviderError


class CircuitBreakerOpen(ProviderError):
    pass


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5, reset_timeout: float = 30.0, clock: Callable[[], float] = time.monotonic):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    def before(self) -> None:
        if self._opened_at is not None and self._clock() - self._opened_at < self.reset_timeout:
            raise CircuitBreakerOpen("AI provider circuit is open")

    def on_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = self._clock()


def call_with_resilience(
    func: Callable[[], object],
    *,
    retries: int = 2,
    breaker: CircuitBreaker | None = None,
    sleep: Callable[[float], None] = time.sleep,
    backoff: float = 0.5,
):
    attempt = 0
    while True:
        if breaker is not None:
            breaker.before()
        try:
            result = func()
        except ProviderError:
            if breaker is not None:
                breaker.on_failure()
            attempt += 1
            if attempt > retries:
                raise
            sleep(backoff * attempt)
            continue
        if breaker is not None:
            breaker.on_success()
        return result
