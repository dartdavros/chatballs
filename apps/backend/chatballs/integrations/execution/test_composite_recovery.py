"""Recovery retains sibling results; nested revocation never gains privileges."""

from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution import checkpoints, contract_testing
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.interpreter import advance
from chatballs.integrations.execution.runner import _commit
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane
from chatballs.integrations.scenario_state.progress import ScenarioProgress
from chatballs.tenancy.database import tenant_atomic


class CompositeRecoveryTests(CompositionCase):
    def test_independent_branch_crash_recovery_does_not_repeat_success(self):
        run = self.start([{"id": "parallel", "kind": "parallel", "branches": [
            [self.action("first")], [self.action("second", connection=self.other_connection)]], "onError": "wait"}])
        # Crash after a fenced result commit, before interpreter joins it.
        for _ in range(10):
            advance(self.tenant, run.public_id, registry=self.registry)
            token = checkpoints.claim(self.tenant, run.public_id)
            if token:
                break
        self.assertIsNotNone(token)
        self.assertTrue(_commit(self.tenant, token, OperationResult(ResultState.COMPLETED, data={"value": "DONE"})))
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 1)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.steps.filter(state="completed").count(), 2)
            result = run.progress.get(path="steps/parallel").definition["result"]
            self.assertEqual(len(result["branches"]), 2)

    def test_stale_fence_cannot_overwrite_a_branch_checkpoint(self):
        run = self.start([self.action("first"), self.action("second")])
        for _ in range(10):
            advance(self.tenant, run.public_id, registry=self.registry)
            first = checkpoints.claim(self.tenant, run.public_id)
            if first:
                break
        with tenant_atomic(self.tenant):
            past = timezone.now() - timedelta(seconds=1)
            run.steps.filter(pk=first.step_id).update(lease_until=past, due_at=past)
            ConnectionExecutionLane.objects.filter(integration=self.integration).update(until=past)
        second = checkpoints.claim(self.tenant, run.public_id)
        self.assertGreater(second.fence, first.fence)
        self.assertFalse(_commit(self.tenant, first, OperationResult(ResultState.COMPLETED, data={"value": "OLD"})))
        self.assertTrue(_commit(self.tenant, second, OperationResult(ResultState.COMPLETED, data={"value": "NEW"})))
        self.pump(run)
        self.assertEqual(self.state(run), "completed")

    def test_runtime_rls_hides_foreign_progress_receipts_and_waits(self):
        run = self.start([{"id": "time", "kind": "wait", "mode": "duration", "duration": 3600}])
        self.pump(run, limit=8)
        def foreign():
            with tenant_atomic(self.other.pk):
                self.assertFalse(ScenarioProgress.objects.filter(run=run).exists())
                from chatballs.integrations.scenario_state.waits import ScenarioWait
                self.assertFalse(ScenarioWait.objects.filter(run=run).exists())
        self.as_runtime(foreign)
