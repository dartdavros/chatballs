"""A long result cannot extend its original persisted deadline forever."""

from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution import checkpoints
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.interpreter import advance
from chatballs.integrations.execution.runner import _commit
from chatballs.tenancy.database import tenant_atomic


class PendingDeadlineTests(CompositionCase):
    def test_pending_continuation_consumes_reserved_capacity(self):
        from chatballs.integrations.execution.budgets import MAX_DATA
        from chatballs.integrations.scenario_state.progress import ScenarioBudget
        run = self.start([self.action("job"), self.action("after")], key="capacity")
        token = None
        for _ in range(16):
            advance(self.tenant, run.public_id, registry=self.registry)
            token = checkpoints.claim(self.tenant, run.public_id)
            if token:
                break
        self.assertIsNotNone(token)
        with tenant_atomic(self.tenant):
            ScenarioBudget.objects.filter(root=run).update(payload_bytes=MAX_DATA)
        result = OperationResult(ResultState.PENDING, continuation={"cursor": "saved"},
                                 deadline=timezone.now() + timedelta(hours=1))
        self.assertTrue(_commit(self.tenant, token, result))
        with tenant_atomic(self.tenant):
            self.assertLessEqual(ScenarioBudget.objects.get(root=run).payload_bytes, MAX_DATA)
            self.assertEqual(run.steps.get().definition["continuation"], {"cursor": "saved"})

    def test_expired_pending_result_is_unknown_and_does_not_start_next_effect(self):
        run = self.start([self.action("job"), self.action("after")])
        token = None
        for _ in range(16):
            advance(self.tenant, run.public_id, registry=self.registry)
            token = checkpoints.claim(self.tenant, run.public_id)
            if token:
                break
        self.assertIsNotNone(token)
        result = OperationResult(ResultState.PENDING, deadline=timezone.now() - timedelta(seconds=1))
        self.assertTrue(_commit(self.tenant, token, result))
        self.pump(run)
        self.assertEqual(self.state(run), "unknown")
        with tenant_atomic(self.tenant):
            self.assertFalse(run.steps.filter(path="steps/after").exists())
            self.assertEqual(run.steps.get().error_code, "outcome_unavailable")
