from django.core.management.base import BaseCommand

from hub_platform.events.services import DomainEvent, enqueue_event


class Command(BaseCommand):
    help = "Enqueues a deterministic local test event for E01 checks."

    def handle(self, *args: object, **options: object) -> None:
        event = enqueue_event(
            DomainEvent(
                aggregate_type="local_check",
                aggregate_id="e01",
                event_type="local_check.requested",
                payload={"source": "emit_test_event"},
            )
        )
        self.stdout.write(str(event.id))
