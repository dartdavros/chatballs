"""Privacy, long results, bounded tool use and employee approval races."""

import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace

from django.db import DatabaseError, transaction
from django.utils import timezone

from chatballs.ai.invocation_jobs import ChatJob
from chatballs.ai.provider.base import ChatMessage, ToolCall
from chatballs.ai.pseudonymization import KnownValue, Pseudonymizer
from chatballs.ai.tool_calls import execute_tool_call
from chatballs.ai.tool_loop import MAX_OPERATIONS, run_tool_loop
from chatballs.ai.tool_loop_testing import ScriptedProvider, calls, says
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution.ai_bridge import plan_actions
from chatballs.integrations.execution.ai_deadlines import expire
from chatballs.integrations.execution.ai_reply import allowed
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_ai_bridge import AgentExecutionCase
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class AgentRuntimeTests(AgentExecutionCase):
    def test_test_chat_keeps_launched_run_visible_after_provider_failure(self):
        run = self.start()
        from chatballs.ai.provider.base import ProviderRejected
        from chatballs.ai.tool_calls import ToolCallRecord
        from chatballs.ai.turn_types import TurnAnswer
        action = {"runId": str(run.public_id), "state": run.state}
        answer = TurnAnswer(error=ProviderRejected("unavailable"), tool_calls=(
            ToolCallRecord(name="action", title="Action", error="", duration_ms=0, action_result=action),))
        plan = SimpleNamespace(skills=SimpleNamespace(support="unknown", items=[]))
        target = "chatballs.ai.test_chat_views."
        with patch(target + "plan_query_embedding"), patch(target + "run_query_embedding"), \
                patch(target + "plan_chat", return_value=plan), patch(target + "run_turn_chat", return_value=answer), \
                patch(target + "record_turn", return_value=""):
            url = f"/api/v1/organizations/{self.organization.public_id}/agents/{self.channel.pk}/test-chat/"
            response = self.client.post(url, {"message": "Run", "executionMode": "execute"}, format="json")
        self.assertEqual(response.status_code, 502, response.content)
        self.assertEqual(response.json()["serviceActions"], [action])

    def tools(self):
        with tenant_atomic(self.tenant), patch("chatballs.integrations.execution.ai_bridge.cached_tool_support", return_value=True):
            return plan_actions(self.agent, self.conversation, registry=self.registry)

    def test_existing_loop_restores_inputs_and_keeps_journal_free_of_values(self):
        tool, _ = self.tools()
        pseudonyms = Pseudonymizer([KnownValue("client_email", "private@example.com")])
        with patch("chatballs.integrations.execution.actions.default_registry", return_value=self.registry):
            content, record = execute_tool_call(ToolCall("call", tool.spec.name, {"value": "[[client_email]]"}),
                {tool.spec.name: tool}, pseudonyms)
        result = json.loads(content)
        self.assertEqual(result["state"], "queued")
        self.assertNotIn("private@example.com", content)
        self.assertNotIn("arguments", record.diagnostic)
        with tenant_atomic(self.tenant):
            run = ScenarioRun.objects.get(public_id=record.action_result["runId"])
            self.assertEqual(run.steps.get().definition["arguments"]["value"], "private@example.com")
            self.assertNotIn("private@example.com", run.content)
            self.assertNotIn("private@example.com", str(list(run.journal.values())))

    def test_long_run_returns_pending_and_revocation_blocks_read_and_reply(self):
        self.operation = replace(self.operation, handlers=replace(self.operation.handlers,
            execute=lambda *_: OperationResult(ResultState.PENDING, deadline=timezone.now() + timedelta(hours=1))))
        self.registry = self.make_registry()
        _, status = self.tools()
        run = self.start()
        run_one(self.tenant, run.public_id, registry=self.registry)
        result = json.loads(status.execute({"runId": str(run.public_id)}, "status"))
        self.assertEqual(result["state"], "pending")
        with tenant_atomic(self.tenant):
            self.assertTrue(allowed(self.tenant, self.conversation.pk, [run.public_id]))
            self.grant.mode = "off"
            self.grant.save()
            self.assertFalse(allowed(self.tenant, self.conversation.pk, [run.public_id]))
        with self.assertRaises(ExecutionDenied):
            status.execute({"runId": str(run.public_id)}, "status2")

    def test_tool_budget_rejects_whole_batch_before_launch(self):
        tool, _ = self.tools()
        provider = ScriptedProvider(calls(*[(tool.spec.name, {"value": "x"})] * (MAX_OPERATIONS + 1)), says("done"))
        job = ChatJob(provider=provider, model="scripted", messages=[ChatMessage("user", "request")],
                      breaker_key=(0, 0), breaker_revision=0)
        with patch("chatballs.ai.tool_loop.run_chat", side_effect=lambda request: provider.chat(
            model=request.model, messages=request.messages, tools=request.tools, params=request.params)):
            result = run_tool_loop(job, [tool], Pseudonymizer())
        self.assertIsNotNone(result.rounds[-1].error)
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())

    def test_expiry_is_a_durable_unsent_cancellation(self):
        run = self.ask()
        with tenant_atomic(self.tenant):
            data = run.definition
            data["ai"]["approvalDeadline"] = (timezone.now() - timedelta(seconds=1)).isoformat()
            run.definition = data
            run.save()
            expire({"runId": str(run.public_id), "path": run.steps.get().path}, self.tenant)
        self.assertEqual(self.state(run), "cancelled")
        self.assertEqual(self.calls, [])

    def test_edit_lock_and_exact_confirmation_do_not_change_scenario(self):
        run = self.ask()
        with tenant_atomic(self.tenant):
            step = run.steps.get()
            digest = invocation_digest(step, run)
        control(tenant=self.tenant, public_id=run.public_id, action="edit", digest=digest)
        with tenant_atomic(self.tenant):
            step.refresh_from_db()
            token = step.definition["editor"]["token"]
        with self.assertRaises(ExecutionDenied):
            control(tenant=self.tenant, public_id=run.public_id, action="revise", digest=digest,
                    arguments={"value": "changed"}, edit_token="wrong")
        with patch("chatballs.integrations.execution.actions.default_registry", return_value=self.registry):
            control(tenant=self.tenant, public_id=run.public_id, action="revise", digest=digest,
                    arguments={"value": "changed"}, edit_token=token)
        with self.assertRaises(ExecutionDenied):
            control(tenant=self.tenant, public_id=run.public_id, action="approve", digest=digest)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.steps.get().definition["arguments"], {"value": "changed"})
            self.scenario.refresh_from_db()
            self.assertEqual(self.scenario.definition["steps"][0]["inputs"]["value"]["value"], "private-input")
            from chatballs.integrations.execution.ai_context import action_context
            facts = action_context(self.agent, self.conversation, Pseudonymizer())
            self.assertIn("changed", facts)
            self.assertNotIn("private-input", facts)
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "completed")

    def test_runtime_rls_hides_foreign_grant_and_checks_parent_tenant(self):
        with tenant_atomic(self.tenant):
            self.assertEqual(self.as_runtime(lambda: AgentActionGrant.objects.count()), 1)
        from chatballs.tenancy.context import TenantContext
        with tenant_atomic(TenantContext.for_resource(self.other)):
            self.assertEqual(self.as_runtime(lambda: AgentActionGrant.objects.count()), 0)
            def cross_tenant_insert():
                with self.assertRaisesMessage(DatabaseError, "cross-tenant relation"), transaction.atomic():
                    AgentActionGrant.objects.bulk_create([AgentActionGrant(
                        organization_id=self.other.pk, agent_id=self.agent.pk, integration_id=self.integration.pk,
                        operation_key="foreign", mode="self")])
            self.as_runtime(cross_tenant_insert)
