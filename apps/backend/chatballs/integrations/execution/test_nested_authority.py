"""Children keep snapshots but never inherit broader or revoked authority."""

from copy import deepcopy

from chatballs.integrations.execution import contract_testing
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.interpreter import advance
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.tenancy.database import tenant_atomic


class NestedAuthorityTests(CompositionCase):
    def nested(self):
        with tenant_atomic(self.tenant):
            document = deepcopy(self.scenario.definition)
            document["steps"] = [self.action("child")]
            document["triggers"] = [{"id": "nested", "kind": "scenario"}]
            document["access"]["delegated"] = True
            child = ScenarioDefinition(organization=self.organization, name="Child", enabled=True)
            child.definition = document
            child.save()
        run = self.start([{"id": "call", "kind": "call", "scenario": str(child.public_id), "inputs": {}}, self.action("after")])
        for _ in range(16):
            advance(self.tenant, run.public_id, registry=self.registry)
            with tenant_atomic(self.tenant):
                nested = run.children.first()
            if nested:
                return run, child, nested
        self.fail("Nested Run was not materialized")

    def test_parent_revocation_stops_child_before_effect(self):
        run, child, nested = self.nested()
        with tenant_atomic(self.tenant):
            self.scenario.enabled = False
            self.scenario.save(update_fields=["enabled"])
        self.pump(nested)
        self.assertEqual(self.state(nested), "failed")
        self.assertEqual(contract_testing.CALLS, [])
        self.pump(run)
        self.assertEqual(self.state(run), "failed")

    def test_current_child_delegation_is_intersected_with_snapshot(self):
        run, child, nested = self.nested()
        with tenant_atomic(self.tenant):
            data = child.definition
            data["access"]["delegated"] = False
            child.definition = data
            child.save()
        self.pump(nested)
        self.assertEqual(self.state(nested), "failed")
        self.assertEqual(contract_testing.CALLS, [])

    def test_child_context_cannot_widen_parent_scope(self):
        run, child, nested = self.nested()
        with tenant_atomic(self.tenant):
            parent = self.scenario.definition
            parent["access"]["scope"] = "conversation"
            self.scenario.definition = parent
            self.scenario.save()
        self.pump(nested)
        self.assertEqual(self.state(nested), "failed")
        self.assertEqual(contract_testing.CALLS, [])
