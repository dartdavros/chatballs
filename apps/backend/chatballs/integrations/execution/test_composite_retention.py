"""Operational cleanup keeps safe block statuses until journal expiry."""

from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.retention import cleanup
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class CompositeRetentionTests(CompositionCase):
    def test_wait_progress_survives_seven_day_cleanup_without_operational_values(self):
        run = self.start([{"id": "decision", "name": "private block name", "kind": "wait", "mode": "duration", "duration": 1}])
        self.pump(run, limit=4)
        with tenant_atomic(self.tenant):
            run.waits.update(deadline=timezone.now() - timedelta(seconds=1))
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        with tenant_atomic(self.tenant):
            ScenarioRun.objects.filter(pk=run.pk).update(finished_at=timezone.now() - timedelta(days=8))
        self.assertEqual(cleanup(self.tenant), 1)
        with tenant_atomic(self.tenant):
            run.refresh_from_db()
            payload = run_payload(run, detail=True, tenant=self.tenant)
            self.assertTrue(payload["dataCleared"])
            self.assertEqual(payload["controls"], [])
            self.assertEqual(payload["steps"][0]["state"], "completed")
            self.assertNotIn("private block name", str(payload))
            self.assertEqual(payload["steps"][0]["arguments"], {})
            self.assertEqual(payload["steps"][0]["result"], {})
            self.assertTrue(payload["progress"])
        self.assertEqual(cleanup(self.tenant), 0)
