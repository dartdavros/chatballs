"""Owner-deferred sources cannot be mistaken for missing business data."""

from unittest.mock import patch

from chatballs.events.models import OutboxEvent
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.source_support import require_supported_sources
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.database import tenant_atomic


class DeferredSourceTests(ExecutionCase):
    def test_deferred_guards_cannot_create_a_run_even_with_negative_or_any_predicates(self):
        conditions = [
            {"kind": "context_present", "path": "conversation.topic", "present": False},
            {"kind": "tag", "scope": "contact", "tag": 1, "present": False},
            {"left": {"source": "context", "path": "conversation.topic"}, "op": "empty"},
            {"left": {"source": "context", "path": "conversation", "transform": "object.get@1",
                      "args": {"path": "topic"}}, "op": "empty"},
        ]
        for guard in conditions:
            with self.subTest(guard=guard), tenant_atomic(self.tenant):
                document = self.scenario.definition
                document["conditions"] = {"mode": "any", "items": [
                    {"kind": "context_present", "path": "contact", "present": False}, guard,
                ]}
                self.scenario.definition = document
                self.scenario.save(update_fields=["content"])
            with self.assertRaisesMessage(ExecutionDenied, "conditions_unavailable"):
                self.launch(approve=False)
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())
            self.assertFalse(OutboxEvent.objects.filter(event_type="integrations.run").exists())
        self.assertEqual(self.calls, [])

    def test_deferred_input_is_hidden_in_catalog_and_denied_at_launch(self):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["steps"][0]["inputs"]["value"] = {"source": "context", "path": "conversation.topic"}
            self.scenario.definition = document
            self.scenario.save(update_fields=["content"])
        url = f"/api/v1/organizations/{self.organization.public_id}/integrations/run-actions/"
        with patch("chatballs.integrations.execution.manual_catalog_queries.default_registry", return_value=self.registry), patch(
                "chatballs.integrations.execution.actions.default_registry", return_value=self.registry):
            response = self.as_runtime(lambda: self.client.get(url))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(any(row["kind"] == "scenario" for row in response.json()["items"]))
        with self.assertRaisesMessage(ExecutionDenied, "conditions_unavailable"):
            self.launch(approve=False)

    def test_literal_payload_is_not_reinterpreted_as_a_deferred_reference(self):
        document = empty_definition()
        document["steps"] = [{"inputs": {"value": {"source": "constant", "value": {
            "source": "context", "path": "conversation.topic",
        }}}}]
        require_supported_sources(document)

    def test_preexisting_queued_snapshot_with_deferred_guard_cannot_send(self):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["conditions"] = {"mode": "all", "items": [
                {"kind": "context_present", "path": "conversation.topic", "present": False},
            ]}
            self.scenario.definition = document
            self.scenario.save(update_fields=["content"])
        # Simulate a snapshot created before the explicit capability gate.
        with patch("chatballs.integrations.execution.conditions.require_supported_sources"):
            run = self.launch()
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "failed")
        self.assertEqual(self.calls, [])
