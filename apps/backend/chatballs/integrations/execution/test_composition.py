"""Crash-safe paths, joins, nested snapshots and technical budgets."""

from copy import deepcopy
from datetime import timedelta

from django.utils import timezone

from chatballs.integrations.execution import contract_testing
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.tenancy.database import tenant_atomic


class CompositionTests(CompositionCase):
    def test_sequence_if_foreach_parallel_across_services_and_snapshot(self):
        with tenant_atomic(self.tenant):
            ledger = Integration.objects.create(organization=self.organization, name="Independent ledger",
                kind="SERVICE", provider="ADAPTER", is_active=True, status="OK")
            ServiceConnectionSettings.objects.create(organization=self.organization, integration=ledger,
                adapter_key="ledger", adapter_version=1, auth_method="public", credentials="{}")
        run = self.start([
            self.action("first"),
            {"id": "choice", "kind": "if", "condition": {"mode": "all", "items": [
                {"left": {"source": "step", "step": "first", "path": "value"}, "op": "eq", "right": {"source": "constant", "value": "HELLO"}}]},
             "then": [self.action("yes", "chosen", ledger)], "else": [self.action("no", "wrong")]},
            {"id": "each", "kind": "foreach", "list": {"source": "constant", "value": ["one", "two"]},
             "concurrency": 5, "body": [self.action("item", {"source": "item", "step": "each"})], "onError": "continue"},
            {"id": "parallel", "kind": "parallel", "branches": [[self.action("left", "left")],
                [self.action("right", "right", ledger)]], "onError": "wait"},
        ])
        with tenant_atomic(self.tenant):
            self.scenario.definition = {**self.scenario.definition, "steps": [self.action("replacement", "wrong")]}
            self.scenario.save()
        self.pump(run)
        with tenant_atomic(self.tenant):
            checkpoints = list(run.progress.values_list("path", "state", "error_code"))
        self.assertEqual(self.state(run), "completed", checkpoints)
        before = list(contract_testing.CALLS)
        self.pump(run, limit=3)
        self.assertEqual(contract_testing.CALLS, before)
        self.assertEqual([row[2]["value"] for row in before], ["hello", "one", "two", "left"])
        with tenant_atomic(self.tenant):
            paths = list(run.steps.values_list("path", flat=True))
            self.assertIn("steps/each/iteration/1/item", paths)
            self.assertEqual(run.progress.get(path="steps/parallel").state, "completed")
            self.assertEqual(set(run.steps.values_list("adapter_key", flat=True)), {"independent", "ledger"})
            self.assertEqual(run.steps.filter(integration=ledger, state="completed").count(), 2)
            from chatballs.integrations.adapters.schema import validate_value
            from chatballs.integrations.execution.result_payloads import schema_and_names
            for path in ("steps/each", "steps/parallel"):
                frame = run.progress.get(path=path)
                spec, _ = schema_and_names(run, frame.definition["block"])
                self.assertEqual(validate_value(spec, frame.definition["result"]), [])

    def test_try_gets_safe_error_and_after_fail_preserves_success(self):
        run = self.start([{"id": "attempt", "kind": "try", "body": [self.action("bad", "fail")],
            "catch": [self.action("caught", {"source": "error", "step": "attempt", "path": "reason"})], "after": "fail"}])
        self.pump(run)
        self.assertEqual(self.state(run), "failed")
        self.assertEqual(len(contract_testing.CALLS), 2)
        self.assertEqual(contract_testing.CALLS[1][2]["value"], "operation_rejected")

    def test_invalid_actual_input_stops_before_next_effect(self):
        run = self.start([self.action("one"), self.action("bad", {"source": "step", "step": "one", "path": "missing"})])
        self.pump(run)
        self.assertEqual(self.state(run), "failed")
        self.assertEqual(len(contract_testing.CALLS), 1)

    def test_durable_time_wait_releases_worker_and_resumes_once(self):
        run = self.start([self.action("before"), {"id": "wait", "kind": "wait", "mode": "duration", "duration": 3600}, self.action("after")])
        self.pump(run, limit=20)
        self.assertEqual(self.state(run), "pending")
        self.assertEqual(len(contract_testing.CALLS), 1)
        with tenant_atomic(self.tenant):
            deadline = run.waits.get().deadline
        self.pump(run, limit=2)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.waits.get().deadline, deadline)
            run.waits.update(deadline=timezone.now() - timedelta(seconds=1))
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(contract_testing.CALLS), 2)

    def test_budget_does_not_truncate_iterations_or_start_effects(self):
        run = self.start([{"id": "loop", "kind": "foreach", "list": {"source": "constant", "value": list(range(1001))},
                          "body": [self.action("item")], "concurrency": 5}])
        self.pump(run)
        self.assertEqual(self.state(run), "failed")
        self.assertEqual(contract_testing.CALLS, [])
        with tenant_atomic(self.tenant):
            self.assertEqual(run.progress.get(path="steps/loop").error_code, "budget_iterations")

    def test_nested_run_snapshot_and_recursion(self):
        with tenant_atomic(self.tenant):
            document = deepcopy(self.scenario.definition)
            document["triggers"] = [{"id": "nested", "kind": "scenario"}]
            document["access"]["delegated"] = True
            document["steps"] = [self.action("child")]
            child = ScenarioDefinition(organization=self.organization, name="Nested", enabled=True)
            child.definition = document
            child.save()
        run = self.start([{"id": "call", "kind": "call", "scenario": str(child.public_id), "inputs": {}}, self.action("after")])
        with tenant_atomic(self.tenant):
            child.definition = {**document, "steps": [self.action("changed", "wrong")]}
            child.save()
        for _ in range(20):
            self.pump(run, limit=2)
            with tenant_atomic(self.tenant):
                children = list(run.children.all())
            for nested in children:
                self.pump(nested)
            if self.state(run) == "completed":
                break
        self.assertEqual(self.state(run), "completed")
        with tenant_atomic(self.tenant):
            self.assertEqual(run.children.count(), 1)
            self.assertEqual(run.children.get().steps.get().path, "steps/child")
            child.definition = {**document, "steps": [{"id": "cycle", "kind": "call", "scenario": str(self.scenario.public_id), "inputs": {}}]}
            child.save()
        with self.assertRaisesRegex(ExecutionDenied, "recursion"):
            self.start([{"id": "call", "kind": "call", "scenario": str(child.public_id), "inputs": {}}], key="cycle")

    def test_cancel_stops_unstarted_effect_and_preserves_partial_result(self):
        run = self.start([self.action("first"), self.action("later")])
        for _ in range(8):
            run_one(self.tenant, run.public_id, registry=self.registry)
            if contract_testing.CALLS:
                break
        control(tenant=self.tenant, public_id=run.public_id, action="cancel")
        self.pump(run)
        self.assertEqual(self.state(run), "cancelled")
        self.assertEqual(len(contract_testing.CALLS), 1)
