import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from hub_platform.events.handlers import dispatch
from hub_platform.events.models import OutboxStatus
from hub_platform.events.services import claim_next_outbox_event, mark_retry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs the local domain event worker."

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write("Hub worker started")
        while True:
            event = claim_next_outbox_event()
            if event is None:
                time.sleep(1)
                continue

            try:
                logger.info("Processing outbox event %s", event.id)
                dispatch(event.event_type, event.payload)
                event.status = OutboxStatus.PROCESSED
                event.processed_at = timezone.now()
                event.save(update_fields=["status", "processed_at"])
            except Exception as exc:  # pragma: no cover
                logger.exception("Outbox event failed: %s", event.id)
                mark_retry(event, str(exc))
