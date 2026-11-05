"""Real pool pressure and per-connection cooldown without external I/O."""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import BoundedSemaphore, Event
from unittest.mock import patch

from django.utils import timezone

from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution import checkpoints, worker
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.launch import launch_direct
from chatballs.integrations.execution.runner import _commit
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    ServiceConnectionSettings,
)
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane
from chatballs.tenancy.database import tenant_atomic


class WorkerLaneTests(ExecutionCase):
    def other_connection(self, name):
        with tenant_atomic(self.tenant):
            integration = Integration.objects.create(organization=self.organization, name=name,
                kind=IntegrationKind.SERVICE, provider=IntegrationProvider.ADAPTER, is_active=True, status="OK")
            source = ServiceConnectionSettings.objects.get(integration=self.integration)
            ServiceConnectionSettings.objects.create(integration=integration,
                adapter_key=source.adapter_key, adapter_version=source.adapter_version,
                auth_method=source.auth_method, credentials="{}")
        return integration

    def direct(self, integration, key):
        run, _ = launch_direct(tenant=self.tenant, connection_id=integration.pk,
            operation_key=self.operation.key, trigger_key=key,
            arguments={"value": "private-input"}, registry=self.registry)
        with tenant_atomic(self.tenant):
            digest = invocation_digest(run.steps.get(), run)
        control(tenant=self.tenant, public_id=run.public_id, action="approve", digest=digest)
        return run

    def test_rate_limit_defers_only_its_connection_and_permanent_error_stops(self):
        first, waiting = self.launch("limited"), self.launch("waiting")
        other = self.direct(self.other_connection("Other service"), "other")
        token = checkpoints.claim(self.tenant, first.public_id)
        before = timezone.now()
        self.assertTrue(_commit(self.tenant, token, OperationResult(
            ResultState.UNKNOWN, error_code="rate_limited", retry_after_seconds=120)))
        self.assertIsNone(checkpoints.claim(self.tenant, waiting.public_id))
        with tenant_atomic(self.tenant):
            step = waiting.steps.get()
            self.assertEqual(step.attempt, 0)
            self.assertGreaterEqual((step.due_at - before).total_seconds(), 120)
        other_token = checkpoints.claim(self.tenant, other.public_id)
        self.assertIsNotNone(other_token)
        self.assertTrue(_commit(self.tenant, other_token, OperationResult(
            ResultState.FAILED, error_code="invalid_arguments")))
        self.assertEqual(self.state(other), "failed")
        self.assertIsNone(checkpoints.claim(self.tenant, other.public_id))

    def test_busy_pool_returns_to_dispatcher_and_durably_reschedules_excess(self):
        runs = [self.launch("first"), self.direct(self.other_connection("Second"), "second"),
                self.direct(self.other_connection("Third"), "third")]
        release, started, finished = Event(), Queue(), Queue()

        def hold_effect(_tenant, public_id, *, token):
            started.put(public_id)
            release.wait(timeout=20)
            finished.put(public_id)

        slots = BoundedSemaphore(2)
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(worker, "_POOL", pool), patch.object(
                worker, "_SLOTS", slots), patch.object(worker, "run_one", side_effect=hold_effect):
            try:
                for run in runs[:2]:
                    worker.dispatch_run({"runId": str(run.public_id)}, self.tenant)
                    self.assertEqual(started.get(timeout=5), str(run.public_id))
                before = timezone.now()
                # Returns while both effects are still blocked. No wait for a
                # free thread, so the caller can dispatch ordinary AI/messages.
                worker.dispatch_run({"runId": str(runs[2].public_id)}, self.tenant)
                self.assertFalse(release.is_set())
                with tenant_atomic(self.tenant):
                    for run in runs[:2]:
                        step = run.steps.get()
                        self.assertEqual(step.state, "running")
                        self.assertTrue(step.lease_until)
                        self.assertTrue(step.run.journal.filter(code="claimed").exists())
                    waiting = runs[2].steps.get()
                    self.assertEqual(waiting.attempt, 0)
                    from chatballs.events.models import OutboxEvent
                    self.assertTrue(OutboxEvent.objects.filter(event_type="integrations.run",
                        payload={"runId": str(runs[2].public_id)}, next_attempt_at__gte=before).exists())
                    self.assertEqual(ConnectionExecutionLane.objects.filter(until__gt=before).count(), 2)
            finally:
                release.set()
                # Join before restoring the patched semaphore used by _run's
                # finally block; otherwise teardown itself introduces a race.
                pool.shutdown(wait=True)
        self.assertEqual(finished.qsize(), 2)
        self.assertTrue(slots.acquire(blocking=False))
        self.assertTrue(slots.acquire(blocking=False))
        self.assertFalse(slots.acquire(blocking=False))
