import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from hub_platform.conversations.poller import poll_all_messengers
from hub_platform.events.handlers import dispatch
from hub_platform.events.models import OutboxStatus
from hub_platform.events.services import claim_next_outbox_event, mark_retry

logger = logging.getLogger(__name__)

MESSENGER_POLL_INTERVAL = 3.0  # seconds between messenger long-poll cycles


class Command(BaseCommand):
    help = "Runs the local domain event worker (outbox dispatch + messenger inbound polling)."

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write("Hub worker started")
        last_poll = 0.0
        while True:
            event = claim_next_outbox_event()
            if event is not None:
                try:
                    logger.info("Processing outbox event %s", event.id)
                    dispatch(event.event_type, event.payload)
                    event.status = OutboxStatus.PROCESSED
                    event.processed_at = timezone.now()
                    event.save(update_fields=["status", "processed_at"])
                except Exception as exc:  # pragma: no cover
                    logger.exception("Outbox event failed: %s", event.id)
                    mark_retry(event, str(exc))
                continue

            now = time.monotonic()
            if now - last_poll >= MESSENGER_POLL_INTERVAL:
                last_poll = now
                try:
                    poll_all_messengers()
                except Exception:  # pragma: no cover
                    logger.exception("Messenger polling cycle failed")
            time.sleep(1)
