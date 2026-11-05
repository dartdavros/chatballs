"""Durable schedule slots and independent recovery under PostgreSQL."""

from datetime import UTC, datetime, timedelta

from chatballs.integrations.automation_events.configuration import synchronize
from chatballs.integrations.automation_events.scheduler import tick
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class SchedulerTests(CompositionCase):
    def prepare(self, misfire):
        now = datetime(2026, 10, 25, 2, tzinfo=UTC)
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["steps"] = [self.action("read")]
            document["access"]["delegated"] = True
            document["triggers"] = [{"kind": "schedule", "id": "daily", "timezone": "Europe/Berlin",
                "frequency": "daily", "time": "02:30", "misfire": misfire,
                "ambiguous": "second", "nonexistent": "skip"}]
            self.scenario.definition = document
            self.scenario.save()
            synchronize(self.tenant, self.scenario, {})
            self.scenario.schedules.update(checked_at=now - timedelta(days=2), due_at=now)
        return now

    def test_once_launches_latest_fold_slot_only_once_across_revision(self):
        now = self.prepare("once")
        tick(self.tenant, now=now, registry=self.registry)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 1)
            row = self.scenario.schedules.get()
            self.assertEqual(row.last_slot, datetime(2026, 10, 25, 1, 30, tzinfo=UTC))
            self.scenario.revision += 1
            self.scenario.save(update_fields=["revision"])
            self.scenario.schedules.update(due_at=now)
        tick(self.tenant, now=now, registry=self.registry)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 1)

    def test_skip_does_not_replay_outage_but_next_due_slot_runs(self):
        now = self.prepare("skip")
        tick(self.tenant, now=now, registry=self.registry)
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())
            due = self.scenario.schedules.get().due_at
        tick(self.tenant, now=due + timedelta(seconds=10), registry=self.registry)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 1)
