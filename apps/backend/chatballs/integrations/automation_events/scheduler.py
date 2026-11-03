"""Short transactional scheduling; the shared runner owns every effect."""

from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.automation_events.schedule_slots import latest_slot, next_slot
from chatballs.integrations.execution.automation import launch_automatic
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.automation import ScheduleCheckpoint
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.tenancy.database import tenant_atomic


def tick(tenant, *, now=None, registry=None):
    now = now or timezone.now()
    with tenant_atomic(tenant):
        ids = list(ScheduleCheckpoint.objects.filter(organization_id=tenant.organization_id,
            due_at__lte=now, scenario__enabled=True).order_by("due_at", "pk").values_list("pk", flat=True)[:50])
    for pk in ids:
        with tenant_atomic(tenant):
            identity = ScheduleCheckpoint.objects.filter(pk=pk).values_list("scenario_id", flat=True).first()
            if not ScenarioDefinition.objects.select_for_update(skip_locked=True).filter(pk=identity).exists():
                continue
            row = ScheduleCheckpoint.objects.select_for_update(skip_locked=True).select_related("scenario").filter(pk=pk).first()
            if row is None or row.due_at > now:
                continue
            trigger = next((t for t in row.scenario.definition["triggers"] if t["id"] == row.trigger_id and t["kind"] == "schedule"), None)
            if trigger is None:
                continue
            slot = latest_slot(trigger, row.checked_at, now)
            # Within a normal poll interval the slot is due, not a misfire.
            execute = slot and (trigger["misfire"] == "once" or now - slot <= timedelta(seconds=60))
            if execute and slot != row.last_slot:
                try:
                    launch_automatic(tenant, row.scenario, trigger,
                        key=f"schedule:{row.trigger_id}:{slot.isoformat()}", registry=registry)
                except ExecutionDenied as error:
                    # Keep the missed slot for once; independent schedules continue.
                    row.due_at = now + timedelta(minutes=1)
                    row.error_code = str(error)
                    row.save(update_fields=["due_at", "error_code"])
                    continue
                row.last_slot = slot
            row.checked_at, row.due_at, row.error_code = now, next_slot(trigger, now), ""
            row.save(update_fields=["checked_at", "due_at", "last_slot", "error_code"])
