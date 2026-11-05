"""Budgets fail visibly before new effects; successful loop items survive recovery."""

from copy import deepcopy

from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution import checkpoints, contract_testing
from chatballs.integrations.execution.block_values import initial
from chatballs.integrations.execution.budgets import MAX_DATA, MAX_INSTANCES
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.frames import create
from chatballs.integrations.execution.interpreter import advance
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import _commit
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.progress import ScenarioBudget
from chatballs.tenancy.database import tenant_atomic


class CompositeLimitTests(CompositionCase):
    def test_volume_time_and_instance_exhaustion_fail_before_effect(self):
        for field, value, reason in (("payload_bytes", MAX_DATA, "budget_volume"),
                                     ("active_seconds", 3600, "budget_execution"),
                                     ("instances", MAX_INSTANCES, "budget_execution")):
            with self.subTest(field=field):
                run = self.start([self.action("one"), self.action("two")], key=field)
                with tenant_atomic(self.tenant):
                    create(run, "steps", "sequence", initial(run), steps=run.definition["document"]["steps"], index=0)
                    ScenarioBudget.objects.filter(root=run).update(**{field: value})
                self.pump(run)
                self.assertEqual(self.state(run), "failed")
                with tenant_atomic(self.tenant):
                    self.assertTrue(run.progress.filter(error_code=reason).exists())
                self.assertEqual(contract_testing.CALLS, [])

    def test_child_initial_cursor_is_reserved_with_the_call(self):
        with tenant_atomic(self.tenant):
            document = deepcopy(self.scenario.definition)
            document["triggers"] = [{"id": "nested", "kind": "scenario"}]
            document["access"]["delegated"] = True
            document["steps"] = [self.action("nested")]
            child = ScenarioDefinition(organization=self.organization, name="Child", enabled=True)
            child.definition = document
            child.save()
        run = self.start([{"id": "call", "kind": "call", "scenario": str(child.public_id), "inputs": {}}])
        with tenant_atomic(self.tenant):
            root = create(run, "steps", "sequence", initial(run), steps=run.definition["document"]["steps"], index=0)
            root.state = "pending"
            root.save(update_fields=["state"])
            create(run, "steps/call", "call", initial(run), parent="steps", block=run.definition["document"]["steps"][0])
            ScenarioBudget.objects.filter(root=run).update(instances=MAX_INSTANCES - 1)
        self.pump(run)
        self.assertEqual(self.state(run), "failed")
        with tenant_atomic(self.tenant):
            self.assertFalse(run.children.exists())
            self.assertEqual(run.progress.get(path="steps/call").error_code, "budget_execution")

    def test_large_launch_parameters_are_rejected_before_snapshot(self):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["parameters"] = {"type": "object", "properties": {"large": {"type": "string"}}}
            document["steps"] = [{"id": "wait", "kind": "wait", "mode": "duration", "duration": 1}]
            self.scenario.definition = document
            self.scenario.save()
        from chatballs.integrations.execution.launch import launch
        with self.assertRaisesMessage(ExecutionDenied, "budget_volume"):
            launch(tenant=self.tenant, scenario_id=self.scenario.public_id, trigger_key="large",
                   parameters={"large": "x" * (1024 * 1024)}, registry=self.registry)

    def test_loop_recovery_keeps_success_and_its_partial_result(self):
        run = self.start([{"id": "loop", "kind": "foreach", "list": {"source": "constant", "value": ["a", "b"]},
            "body": [self.action("item", {"source": "item", "step": "loop"})], "concurrency": 1}])
        token = None
        for _ in range(20):
            advance(self.tenant, run.public_id, registry=self.registry)
            token = checkpoints.claim(self.tenant, run.public_id)
            if token:
                break
        self.assertIsNotNone(token)
        self.assertTrue(_commit(self.tenant, token, OperationResult(ResultState.COMPLETED, data={"value": "SAVED"})))
        self.pump(run)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual([call[2]["value"] for call in contract_testing.CALLS], ["b"])
        with tenant_atomic(self.tenant):
            items = run.progress.get(path="steps/loop").definition["result"]["items"]
            self.assertEqual([entry["steps"]["item"]["value"] for entry in items], ["SAVED", "B"])
