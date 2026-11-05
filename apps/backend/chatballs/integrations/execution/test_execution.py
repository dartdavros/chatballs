"""PostgreSQL execution-boundary tests; no HTTP server or product demo data."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.utils import timezone

from chatballs.events.models import OutboxEvent
from chatballs.integrations.adapters.bitrix24 import ADAPTER
from chatballs.integrations.adapters.contracts import (
    Effect,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.adapters.registry import build_registry
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.execution import checkpoints
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.launch import launch
from chatballs.integrations.execution.runner import _commit, _send_marker, run_one
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    ServiceConnectionSettings,
)
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.test_api import ScenarioAPICase
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class ExecutionCase(ScenarioAPICase):
    def setUp(self):
        super().setUp()
        self.tenant = TenantContext.for_membership(self.owner.memberships.get(organization=self.organization))
        self.calls = []
        self.operation = OperationDescriptor(key="test.effect", title_key="services.bitrix24.preset_lead_title",
            effect=Effect.CREATE, input=TypeSpec("object", properties=(("value", TypeSpec("string", required=True)),)),
            output=TypeSpec("object"), handlers=OperationHandlers(execute=self.effect))
        self.registry = self.make_registry()
        with tenant_atomic(self.tenant):
            self.integration = Integration.objects.create(organization=self.organization, name="Execution boundary",
                kind=IntegrationKind.SERVICE, provider=IntegrationProvider.ADAPTER, is_active=True, status="OK")
            ServiceConnectionSettings.objects.create(integration=self.integration, adapter_key=ADAPTER.key,
                adapter_version=ADAPTER.contract_version, auth_method=ADAPTER.auth_methods[0].key, credentials="{}")
            document = empty_definition()
            document["access"]["scope"] = "organization"
            document["steps"] = [{"id": "one", "kind": "action", "connection": str(self.integration.pk),
                "target": "service:test.effect", "inputs": {"value": {"source": "constant", "value": "private-input"}}}]
            self.scenario = ScenarioDefinition(organization=self.organization, name="Boundary", enabled=True)
            self.scenario.definition = document
            self.scenario.save()

    def make_registry(self):
        registry = build_registry([])
        registry.register_adapter(replace(ADAPTER, operations=(self.operation,), templates=(), lookups=(), entities=(),
            auth_methods=(replace(ADAPTER.auth_methods[0], check=None),)))
        return registry

    def effect(self, context, operation, arguments):
        self.assertFalse(connection.in_atomic_block)
        with tenant_atomic(self.tenant):
            step = ScenarioStep.objects.get(effect_key=context.effect_key)
            self.assertIsNotNone(step.sent_at)
        self.calls.append(context.effect_key)
        return OperationResult(ResultState.COMPLETED, data={})

    def launch(self, key="click", approve=True):
        run, _created = launch(tenant=self.tenant, scenario_id=self.scenario.public_id,
            trigger_key=key, parameters={}, registry=self.registry)
        if approve:
            with tenant_atomic(self.tenant):
                digest = invocation_digest(run.steps.get(), run)
            control(tenant=self.tenant, public_id=run.public_id, action="approve", digest=digest)
        return run

    def state(self, run):
        with tenant_atomic(self.tenant):
            return ScenarioRun.objects.get(pk=run.pk).state

    def expire(self, run):
        with tenant_atomic(self.tenant):
            past = timezone.now() - timedelta(seconds=1)
            run.steps.update(lease_until=past, due_at=past)
            ConnectionExecutionLane.objects.filter(integration=self.integration).update(until=past, cooldown_until=None)

class ExecutionTests(ExecutionCase):
    def test_dedup_survives_revision_and_snapshot_is_encrypted(self):
        run = self.launch(approve=False)
        with tenant_atomic(self.tenant):
            self.scenario.revision += 1
            self.scenario.save(update_fields=["revision"])
        other = self.launch(approve=False)
        self.assertEqual(other.pk, run.pk)
        self.assertNotIn("private-input", run.content)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.steps.count(), 1)
            self.assertFalse(OutboxEvent.objects.filter(payload__icontains="private-input").exists())

    def test_run_step_and_outbox_rollback_together(self):
        with patch("chatballs.integrations.execution.launch.schedule", side_effect=RuntimeError("rollback")):
            self.operation = replace(self.operation, effect=Effect.READ, retry=RetryStrategy.SAFE_READ)
            self.registry = self.make_registry()
            with self.assertRaises(RuntimeError):
                self.launch(approve=False)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 0)
            self.assertEqual(ScenarioStep.objects.count(), 0)

    def test_confirmed_effect_is_not_repeated_and_io_has_no_transaction(self):
        run = self.launch()
        run_one(self.tenant, run.public_id, registry=self.registry)
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(self.calls), 1)

    def test_stale_claim_cannot_overwrite_new_result(self):
        run = self.launch()
        first = checkpoints.claim(self.tenant, run.public_id)
        self.expire(run)
        second = checkpoints.claim(self.tenant, run.public_id)
        self.assertGreater(second.fence, first.fence)
        self.assertFalse(_commit(self.tenant, first, OperationResult(ResultState.COMPLETED, data={})))
        self.assertTrue(_commit(self.tenant, second, OperationResult(ResultState.COMPLETED, data={})))
        self.assertFalse(_commit(self.tenant, first, OperationResult(ResultState.FAILED)))
        self.assertEqual(self.state(run), "completed")

    def test_crash_after_send_without_safe_strategy_stays_unknown(self):
        run = self.launch()
        token = checkpoints.claim(self.tenant, run.public_id)
        self.assertTrue(_send_marker(self.tenant, token, "execute", self.registry))
        self.expire(run)
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "unknown")
        self.assertEqual(self.calls, [])

    def test_lost_response_uses_same_key_or_reconcile_without_second_write(self):
        for strategy in (RetryStrategy.IDEMPOTENCY_KEY, RetryStrategy.RECONCILE, RetryStrategy.SAFE_READ):
            with self.subTest(strategy=strategy):
                calls, reads = [], []
                def effect(context, _operation, _arguments, calls=calls):
                    self.assertFalse(connection.in_atomic_block)
                    calls.append(context.effect_key)
                    return OperationResult(ResultState.UNKNOWN) if len(calls) == 1 else OperationResult(ResultState.COMPLETED, data={})
                def reconcile(context, _operation, _arguments, reads=reads):
                    reads.append(context.effect_key)
                    return OperationResult(ResultState.COMPLETED, data={})
                self.operation = replace(self.operation, retry=strategy,
                    effect=Effect.READ if strategy == RetryStrategy.SAFE_READ else Effect.CREATE,
                    handlers=OperationHandlers(execute=effect, reconcile=reconcile if strategy == RetryStrategy.RECONCILE else None))
                self.registry = self.make_registry()
                run = self.launch(key=strategy, approve=strategy != RetryStrategy.SAFE_READ)
                run_one(self.tenant, run.public_id, registry=self.registry)
                self.expire(run)
                run_one(self.tenant, run.public_id, registry=self.registry)
                self.assertEqual(self.state(run), "completed")
                if strategy == RetryStrategy.RECONCILE:
                    self.assertEqual(reads, calls)
                    self.assertEqual(len(calls), 1)
                else:
                    self.assertEqual(calls[0], calls[1])

    def test_cancel_and_disable_before_send_stop_effect(self):
        run = self.launch()
        control(tenant=self.tenant, public_id=run.public_id, action="cancel")
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "cancelled")
        other = self.launch(key="other")
        with tenant_atomic(self.tenant):
            self.integration.is_active = False
            self.integration.save(update_fields=["is_active"])
        run_one(self.tenant, other.public_id, registry=self.registry)
        self.assertEqual(self.state(other), "failed")
        self.assertEqual(self.calls, [])

    def test_exact_approval_is_required(self):
        run = self.launch(approve=False)
        from chatballs.integrations.execution.permissions import ExecutionDenied
        with self.assertRaises(ExecutionDenied):
            control(tenant=self.tenant, public_id=run.public_id, action="approve", digest="changed")
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "approval")
        self.assertEqual(self.calls, [])
