"""Only execution retention, its delay and protected recovery data."""

from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.retention import (
    cleanup,
    effective_days,
    policy_for,
    update_policy,
)
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class RetentionTests(ExecutionCase):
    def finished(self, age):
        run = self.launch(key=f"age-{age}")
        run_one(self.tenant, run.public_id, registry=self.registry)
        with tenant_atomic(self.tenant):
            ScenarioRun.objects.filter(pk=run.pk).update(finished_at=timezone.now() - timedelta(days=age))
        return run

    def test_default_seven_thirty_and_minimal_dedup_tombstone(self):
        recent, old = self.finished(8), self.finished(31)
        cleanup(self.tenant)
        with tenant_atomic(self.tenant):
            recent.refresh_from_db()
            old.refresh_from_db()
            self.assertEqual(recent.content, "")
            self.assertTrue(recent.journal.exists())
            self.assertTrue(recent.steps.exists())
            self.assertFalse(old.journal.exists())
            self.assertFalse(old.steps.exists())
            self.assertEqual(old.structure, {})
            self.assertIsNone(old.initiator_id)
            self.assertIsNone(old.conversation_id)
            self.assertTrue(old.trigger_key)
        self.assertEqual(cleanup(self.tenant), 0)

    def test_active_wait_and_reconciliation_data_are_protected(self):
        run = self.launch()
        with tenant_atomic(self.tenant):
            ScenarioRun.objects.filter(pk=run.pk).update(created_at=timezone.now() - timedelta(days=100), state="pending")
        self.assertEqual(cleanup(self.tenant), 0)
        with tenant_atomic(self.tenant):
            run.refresh_from_db()
            self.assertTrue(run.content)
            self.assertTrue(run.steps.get().content)

    def test_shortening_requires_confirmation_waits_24h_and_can_be_cancelled(self):
        run = self.finished(5)
        with self.assertRaises(ExecutionDenied):
            update_policy(self.tenant, step_days=3, journal_days=30, version=1)
        row = update_policy(self.tenant, step_days=3, journal_days=30, version=1, confirmed=True)
        self.assertGreaterEqual(row.effective_at, timezone.now() + timedelta(hours=23, minutes=59))
        self.assertEqual(effective_days(row), (7, 30))
        self.assertEqual(cleanup(self.tenant), 0)
        row = update_policy(self.tenant, step_days=7, journal_days=30, version=row.version)
        self.assertIsNone(row.effective_at)
        self.assertEqual(cleanup(self.tenant), 0)
        with tenant_atomic(self.tenant):
            run.refresh_from_db()
            self.assertIsNone(run.data_cleared_at)

    def test_pending_decrease_does_not_postpone_ordinary_cleanup(self):
        run = self.finished(8)
        row = update_policy(self.tenant, step_days=3, journal_days=30, version=1, confirmed=True)
        self.assertEqual(cleanup(self.tenant), 1)
        row.effective_at = timezone.now() - timedelta(seconds=1)
        with tenant_atomic(self.tenant):
            row.save(update_fields=["effective_at"])
            run.refresh_from_db()
            self.assertIsNotNone(run.data_cleared_at)

    def test_only_manager_can_change_policy_and_details_cannot_outlive_history(self):
        tenant = TenantContext.for_membership(self.employee.memberships.get(organization=self.organization))
        with self.assertRaises(ExecutionDenied):
            update_policy(tenant, step_days=7, journal_days=30, version=1)
        with self.assertRaises(ExecutionDenied):
            update_policy(self.tenant, step_days=31, journal_days=30, version=1)
        with tenant_atomic(self.tenant):
            self.assertEqual(policy_for(self.tenant).version, 1)
