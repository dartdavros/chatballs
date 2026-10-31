"""Exact manual consent and immutable operation identities."""

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from chatballs.events.models import OutboxEvent
from chatballs.integrations.execution.launch import launch
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class PlanTests(ExecutionCase):
    def preview(self):
        return launch(tenant=self.tenant, scenario_id=self.scenario.public_id, trigger_key="click",
                      parameters={}, registry=self.registry, preview=True)[0]

    def test_preview_has_no_run_or_outbox_then_exact_consent_queues_once(self):
        preview = self.preview()
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 0)
            self.assertFalse(OutboxEvent.objects.filter(event_type="integrations.run").exists())
        self.assertNotIn("private-input", preview["confirmation"])
        run, created = launch(tenant=self.tenant, scenario_id=self.scenario.public_id, trigger_key="click",
            parameters={}, registry=self.registry, confirmation=preview["confirmation"])
        self.assertTrue(created)
        self.assertEqual(run.state, "queued")
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(self.calls), 1)

    def test_revision_or_values_changed_after_preview_require_new_consent(self):
        preview = self.preview()
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["steps"][0]["inputs"]["value"]["value"] = "changed"
            self.scenario.definition = document
            self.scenario.revision += 1
            self.scenario.save(update_fields=["content", "revision"])
        with self.assertRaises(ExecutionDenied):
            launch(tenant=self.tenant, scenario_id=self.scenario.public_id, trigger_key="click",
                parameters={}, registry=self.registry, confirmation=preview["confirmation"])
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())

    def test_expired_or_tampered_plan_never_creates_run(self):
        preview = self.preview()
        for token in (preview["confirmation"] + "tampered", preview["confirmation"]):
            with patch("chatballs.integrations.execution.plans.timezone.now", return_value=timezone.now() + timedelta(hours=1)):
                with self.assertRaises(ExecutionDenied):
                    launch(tenant=self.tenant, scenario_id=self.scenario.public_id, trigger_key="click",
                        parameters={}, registry=self.registry, confirmation=token)
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())
