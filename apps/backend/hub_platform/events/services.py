from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from hub_platform.events.context import get_correlation_id
from hub_platform.events.models import OutboxEvent, OutboxStatus


@dataclass(frozen=True)
class DomainEvent:
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict[str, Any]


def enqueue_event(event: DomainEvent) -> OutboxEvent:
    return OutboxEvent.objects.create(
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        event_type=event.event_type,
        payload=event.payload,
        correlation_id=get_correlation_id(),
    )


def mark_retry(event: OutboxEvent, error: str, max_attempts: int = 5) -> None:
    event.attempts += 1
    event.last_error = error
    event.status = OutboxStatus.DEAD_LETTER if event.attempts >= max_attempts else OutboxStatus.FAILED
    event.next_attempt_at = timezone.now() + timedelta(seconds=min(300, 2**event.attempts))
    event.save(update_fields=["attempts", "last_error", "status", "next_attempt_at"])


def claim_next_outbox_event() -> OutboxEvent | None:
    with transaction.atomic():
        event = (
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(
                status__in=[OutboxStatus.PENDING, OutboxStatus.FAILED],
                next_attempt_at__lte=timezone.now(),
            )
            .order_by("next_attempt_at", "created_at")
            .first()
        )
        if event is None:
            return None
        event.status = OutboxStatus.PROCESSING
        event.save(update_fields=["status"])
        return event
