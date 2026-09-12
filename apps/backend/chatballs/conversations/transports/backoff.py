"""Пауза между попытками опроса подключения после сбоя.

Воркер опрашивает мессенджеры каждые три секунды. Подключение с отозванным
токеном или недоступным сервером отвечало ошибкой на каждый цикл и писало
её в журнал двадцать раз в минуту — журнал переставал быть читаемым, а
чужой сервер получал бессмысленный поток запросов. Теперь после сбоя
подключение пропускается с растущей паузой, а в журнал попадают только
изменения состояния: первый сбой, выход на максимальную паузу и
восстановление.

Состояние живёт в памяти процесса: воркер один, а после перезапуска первая
попытка всё равно нужна.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Первая пауза — два цикла опроса, дальше удвоение до четверти часа.
FIRST_DELAY_SECONDS = 6.0
MAX_DELAY_SECONDS = 900.0


@dataclass
class _Failure:
    failures: int
    next_attempt_at: float
    delay: float


_failures: dict[int, _Failure] = {}


def _now() -> float:
    return time.monotonic()


def should_skip(integration_id: int) -> bool:
    state = _failures.get(integration_id)
    return state is not None and _now() < state.next_attempt_at


def record_failure(integration, error: object) -> None:
    previous = _failures.get(integration.id)
    failures = (previous.failures if previous else 0) + 1
    delay = min(FIRST_DELAY_SECONDS * 2 ** (failures - 1), MAX_DELAY_SECONDS)
    _failures[integration.id] = _Failure(failures=failures, next_attempt_at=_now() + delay, delay=delay)
    if failures == 1:
        logger.warning(
            "%s poll failed for integration %s: %s (next attempt in %.0fs)",
            integration.provider, integration.id, error, delay,
        )
    elif delay >= MAX_DELAY_SECONDS and (previous is None or previous.delay < MAX_DELAY_SECONDS):
        logger.warning(
            "%s poll keeps failing for integration %s: %s (retrying every %.0f min)",
            integration.provider, integration.id, error, MAX_DELAY_SECONDS / 60,
        )


def record_success(integration) -> None:
    state = _failures.pop(integration.id, None)
    if state is not None:
        logger.info(
            "%s poll recovered for integration %s after %s failure(s)",
            integration.provider, integration.id, state.failures,
        )


def reset() -> None:
    """Для тестов: забыть все сбои."""

    _failures.clear()
