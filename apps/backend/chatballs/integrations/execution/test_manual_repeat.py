"""HTTP repetition rechecks all known manual authority before a new effect."""

from dataclasses import replace
from unittest.mock import patch

from chatballs.conversations.comment_test_base import CommentTestBase
from chatballs.events.models import OutboxEvent
from chatballs.integrations.adapters.contracts import Effect, RetryStrategy
from chatballs.integrations.execution.launch import launch
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class ManualRepeatTests(ExecutionCase):
    def test_compound_repeat_after_native_grant_revocation_cannot_queue_an_earlier_service_step(self):
        self.operation = replace(self.operation, effect=Effect.READ, retry=RetryStrategy.SAFE_READ)
        self.registry = self.make_registry()
        member = self.employee.memberships.get(organization=self.organization)
        actor = TenantContext.for_membership(member)
        with tenant_atomic(self.tenant):
            conversation = CommentTestBase.make_conversation(self.organization, "manual-repeat")
            document = self.scenario.definition
            document["access"].update(scope="conversation", staff=[self.employee.pk])
            document["steps"].append({"id": "comments", "kind": "action", "connection": "chatballs",
                "target": "chatballs:comments.get", "inputs": {
                    "conversation_id": {"source": "context", "path": "conversation.id"}}})
            self.scenario.definition = document
            self.scenario.save(update_fields=["content"])
            grant = ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="comments.get", operation_key="", scope="conversation")
        source, _ = launch(tenant=actor, scenario_id=self.scenario.public_id, trigger_key="original-compound",
            parameters={}, conversation_id=conversation.pk, registry=self.registry, manual_validation=True)
        for _ in range(32):
            run_one(actor, source.public_id, registry=self.registry)
            if self.state(source) == "completed":
                break
        self.assertEqual(self.state(source), "completed")
        self.assertEqual(len(self.calls), 1)
        with tenant_atomic(self.tenant):
            grant.enabled = False
            grant.save(update_fields=["enabled"])
            runs_before = ScenarioRun.objects.count()
            queued_before = OutboxEvent.objects.filter(event_type="integrations.run").count()
        url = f"/api/v1/organizations/{self.organization.public_id}/integrations/runs/{source.public_id}/repeat/"
        with patch("chatballs.integrations.execution.actions.default_registry", return_value=self.registry):
            response = self.as_runtime(lambda: self.client_for(self.employee).post(url, {
                "triggerKey": "repeat-after-revocation", "acknowledged": str(source.public_id),
                "manual_validation": False,
            }, format="json"))
        self.assertEqual(response.status_code, 409, response.content)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), runs_before)
            self.assertEqual(OutboxEvent.objects.filter(event_type="integrations.run").count(), queued_before)
        self.assertEqual(self.state(source), "completed")
        self.assertEqual(len(self.calls), 1)
