import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from hub_platform.conversations.maintenance import close_stale_conversations
from hub_platform.conversations.poller import poll_all_messengers
from hub_platform.events.handlers import dispatch
from hub_platform.events.models import OutboxStatus
from hub_platform.events.services import claim_next_outbox_event, mark_retry
from hub_platform.notifications.binding import poll_notifier_bots

logger = logging.getLogger(__name__)

MESSENGER_POLL_INTERVAL = 3.0  # seconds between messenger long-poll cycles
MAINTENANCE_INTERVAL = 3600.0  # seconds between maintenance cycles (auto-close stale dialogs)


class Command(BaseCommand):
    help = "Runs the local domain event worker (outbox dispatch + messenger inbound polling)."

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write("Hub worker started")
        last_poll = 0.0
        last_maintenance = 0.0
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
                try:
                    poll_notifier_bots()
                except Exception:  # pragma: no cover
                    logger.exception("Notifier polling cycle failed")
            if now - last_maintenance >= MAINTENANCE_INTERVAL:
                last_maintenance = now
                try:
                    close_stale_conversations()
                except Exception:  # pragma: no cover
                    logger.exception("Maintenance cycle failed")
            time.sleep(1)
