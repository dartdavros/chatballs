import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from hub_platform.calls.maintenance import expire_stale_calls
from hub_platform.conversations.maintenance import close_stale_conversations
from hub_platform.conversations.poller import poll_all_messengers
from hub_platform.events.handlers import dispatch
from hub_platform.events.models import OutboxStatus
from hub_platform.events.services import claim_next_outbox_event, mark_retry
from hub_platform.identity.models import Organization
from hub_platform.notifications.binding import poll_notifier_bots
from hub_platform.tenancy.context import TenantActorKind, TenantContext
from hub_platform.tenancy.database import tenant_atomic

logger = logging.getLogger(__name__)

MESSENGER_POLL_INTERVAL = 3.0  # seconds between messenger long-poll cycles
MAINTENANCE_INTERVAL = 3600.0  # seconds between maintenance cycles (auto-close stale dialogs)
CALL_SWEEP_INTERVAL = 10.0  # seconds between call timeout sweeps (invite expiry, stuck connect)


class Command(BaseCommand):
    help = "Runs the local domain event worker (outbox dispatch + messenger inbound polling)."

    @staticmethod
    def _tenant_contexts():
        for organization in Organization.objects.order_by("id").iterator():
            yield TenantContext.for_resource(
                organization, actor_kind=TenantActorKind.SYSTEM
            )

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write("Hub worker started")
        last_poll = 0.0
        last_maintenance = 0.0
        last_call_sweep = 0.0
        while True:
            try:
                event = claim_next_outbox_event()
            except Exception:  # pragma: no cover
                # Отравленное событие не должно ронять процесс: иначе воркер
                # уходит в краш-петлю и вместе с outbox встают поллинг
                # мессенджеров и таймауты звонков.
                logger.exception("Outbox claim cycle failed")
                time.sleep(1)
                continue
            if event is not None:
                try:
                    logger.info("Processing outbox event %s", event.id)
                    dispatch(event)
                    event.status = OutboxStatus.PROCESSED
                    event.processed_at = timezone.now()
                    event.save(
                        using="platform",
                        update_fields=["status", "processed_at"],
                    )
                except Exception as exc:  # pragma: no cover
                    logger.exception("Outbox event failed: %s", event.id)
                    mark_retry(event, str(exc))
                continue

            now = time.monotonic()
            if now - last_poll >= MESSENGER_POLL_INTERVAL:
                last_poll = now
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            poll_all_messengers(context)
                except Exception:  # pragma: no cover
                    logger.exception("Messenger polling cycle failed")
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            poll_notifier_bots(context)
                except Exception:  # pragma: no cover
                    logger.exception("Notifier polling cycle failed")
            if now - last_call_sweep >= CALL_SWEEP_INTERVAL:
                last_call_sweep = now
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            expire_stale_calls(context)
                except Exception:  # pragma: no cover
                    logger.exception("Call sweep cycle failed")
            if now - last_maintenance >= MAINTENANCE_INTERVAL:
                last_maintenance = now
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            close_stale_conversations(context)
                except Exception:  # pragma: no cover
                    logger.exception("Maintenance cycle failed")
            time.sleep(1)
