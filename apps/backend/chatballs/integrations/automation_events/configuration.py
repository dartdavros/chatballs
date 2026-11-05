"""Explicit editing updates delegation/checkpoints, never launches effects."""

import hashlib
import json

from django.utils import timezone

from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.scenario_state.automation import (
    EventSubscription,
    ScenarioAutomation,
    ScheduleCheckpoint,
)


def synchronize(tenant, scenario, previous):
    document = scenario.definition
    state, _ = ScenarioAutomation.objects.get_or_create(organization_id=scenario.organization_id, scenario=scenario)
    delegated = document["access"]["delegated"]
    if delegated and (not previous.get("access", {}).get("delegated") or state.delegate_id is None):
        actor = current_actor(tenant)
        if actor.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
            raise ExecutionDenied("permission")
        state.delegate = actor.membership
        state.authorized_at = timezone.now()
    elif not delegated:
        state.delegate = None
        state.authorized_at = None
    state.save()
    events = [t for t in document["triggers"] if t["kind"] in {"chatballs", "service"}]
    scenario.event_subscriptions.exclude(trigger_id__in=[t["id"] for t in events]).delete()
    for trigger in events:
        EventSubscription.objects.update_or_create(organization_id=scenario.organization_id,
            scenario=scenario, trigger_id=trigger["id"], defaults={"active": scenario.enabled and delegated,
                "event_key": trigger["event"], "integration_id": trigger.get("connection") if trigger["kind"] == "service" else None})
    triggers = [t for t in document["triggers"] if t["kind"] == "schedule"]
    scenario.schedules.exclude(trigger_id__in=[t["id"] for t in triggers]).delete()
    for trigger in triggers:
        digest = hashlib.sha256(json.dumps(trigger, sort_keys=True).encode()).hexdigest()
        row = scenario.schedules.filter(trigger_id=trigger["id"]).first()
        if row is None or row.configuration_hash != digest:
            now = timezone.now()
            from chatballs.integrations.automation_events.schedule_slots import next_slot
            due = next_slot(trigger, now)
            if row is None:
                row = ScheduleCheckpoint(organization_id=scenario.organization_id, scenario=scenario, trigger_id=trigger["id"])
            row.configuration_hash, row.checked_at, row.due_at = digest, now, due
            row.save()
