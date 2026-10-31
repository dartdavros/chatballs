"""Actual competing database sessions: dedup, lease and forced tenant isolation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

from django.db import close_old_connections

from chatballs.events.models import OutboxEvent
from chatballs.integrations.adapters.contracts import Effect, RetryStrategy
from chatballs.integrations.execution.checkpoints import claim
from chatballs.integrations.execution.launch import launch
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class ExecutionRaceTests(ExecutionCase):
    def compete(self, operation):
        barrier = Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(worker) for _ in range(2)]
            return [result.result(timeout=30) for result in pending]

    def test_concurrent_launch_creates_one_snapshot_step_and_outbox(self):
        self.operation = replace(self.operation, effect=Effect.READ, retry=RetryStrategy.SAFE_READ)
        self.registry = self.make_registry()
        results = self.compete(lambda: launch(tenant=self.tenant, scenario_id=self.scenario.public_id,
            trigger_key="same-event", parameters={}, registry=self.registry))
        self.assertEqual(len({run.pk for run, _created in results}), 1)
        self.assertEqual(sum(created for _run, created in results), 1)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 1)
            self.assertEqual(results[0][0].steps.count(), 1)
            self.assertEqual(OutboxEvent.objects.filter(event_type="integrations.run").count(), 1)

    def test_competing_claims_have_one_winner(self):
        run = self.launch()
        claims = self.compete(lambda: claim(self.tenant, run.public_id))
        self.assertEqual(sum(token is not None for token in claims), 1)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.steps.get().attempt, 1)

    def test_runtime_role_cannot_read_other_tenant_run(self):
        run = self.launch()
        def visible():
            with tenant_atomic(self.other.pk):
                return ScenarioRun.objects.filter(pk=run.pk).exists()
        self.assertFalse(self.as_runtime(visible))
