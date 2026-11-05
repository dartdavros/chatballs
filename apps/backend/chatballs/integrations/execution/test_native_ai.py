"""Explicit native AI grants retain source authors, approvals and safe provenance."""

import json
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from chatballs.ai.provider.base import ToolCall
from chatballs.ai.pseudonymization import KnownValue, Pseudonymizer
from chatballs.ai.tool_calls import execute_tool_call
from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.models import Message
from chatballs.identity.administration_payloads import audit_event_payload
from chatballs.identity.audit import record_audit_event
from chatballs.identity.audit_context import KEY
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.execution.agent_actions import change_policy
from chatballs.integrations.execution.ai_policy import bind
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.native_ai_testing import NativeAICase
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeAITests(NativeAICase):
    def test_existing_source_audit_identifies_agent_and_delegate_without_duplicate_effect(self):
        with tenant_atomic(self.context):
            change_policy(self.context, self.agent, "native:conversations.priority.post", "self", 0)
            self.grant = AgentActionGrant.objects.get(agent=self.agent, native_key="conversations.priority.post")
            self.binding = bind(self.grant, self.conversation)
        run = self.start(arguments={"priority": "HIGH"})
        with patch("chatballs.integrations.execution.runner._commit", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.conversation.refresh_from_db()
            self.assertNotEqual(self.conversation.priority, "HIGH")
            self.assertFalse(AuditEvent.objects.filter(action="conversations.priority_changed").exists())
            self.assertFalse(AuditEvent.objects.filter(action="integrations.native_action_executed").exists())
            past = timezone.now() - timedelta(seconds=1)
            run.steps.update(lease_until=past, due_at=past)
        self.execute(run)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.conversation.refresh_from_db()
            self.assertEqual(self.conversation.priority, "HIGH")
            event = AuditEvent.objects.get(action="conversations.priority_changed")
            self.assertEqual(event.actor_id, self.user.pk)
            self.assertEqual(event.payload[KEY]["delegateMembershipId"], self.member.pk)
            self.assertEqual(event.payload[KEY]["agentId"], self.agent.pk)
            self.assertEqual(AuditEvent.objects.filter(action="integrations.native_action_executed").count(), 1)

    def test_native_io_export_retains_typed_file_and_delegate_audit(self):
        with tenant_atomic(self.context):
            change_policy(self.context, self.agent, "native:reports.support_csv.get", "self", 0)
            self.grant = AgentActionGrant.objects.get(agent=self.agent, native_key="reports.support_csv.get")
            self.binding = bind(self.grant, self.conversation)
        run = self.start(arguments=self.filters())
        self.execute(run)
        with tenant_atomic(self.context):
            result = run.steps.get().definition["result"]
        name, content_type, _body = self.read_result(run, result)
        self.assertEqual((name, content_type), ("support-report.csv", "text/csv; charset=utf-8"))
        with tenant_atomic(self.context):
            audit = AuditEvent.objects.get(action="integrations.native_action_executed")
            self.assertEqual(audit.actor_id, self.user.pk)
            self.assertEqual(audit.payload[KEY]["runId"], str(run.public_id))

    def test_tool_restores_private_input_and_runner_keeps_source_author_once(self):
        tool, status = self.tools()
        self.assertNotIn("conversation_id", tool.spec.parameters["properties"])
        content, record = execute_tool_call(ToolCall("comment", tool.spec.name,
            {"text": "[[client_email]]"}), {tool.spec.name: tool},
            Pseudonymizer([KnownValue("client_email", "private@example.com")]))
        self.assertEqual(json.loads(content)["state"], "queued")
        self.assertNotIn("private@example.com", str(record.diagnostic))
        with tenant_atomic(self.context):
            run = ScenarioRun.objects.get(public_id=record.action_result["runId"])
            self.assertEqual(run.initiator_id, self.member.pk)
            self.assertNotIn("private@example.com", run.content)
        self.execute(run)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            comment = ConversationComment.objects.get(organization=self.organization)
            self.assertEqual((comment.author_id, comment.text, comment.audience),
                (self.user.pk, "private@example.com", "INTERNAL"))
            self.assertFalse(Message.objects.filter(conversation=self.conversation).exists())
            audit = AuditEvent.objects.get(action="integrations.native_action_executed")
            metadata = audit.payload[KEY]
            self.assertEqual((metadata["agentId"], metadata["delegateMembershipId"], metadata["runId"]),
                (self.agent.pk, self.member.pk, str(run.public_id)))
            payload = audit_event_payload(audit)
            self.assertIn(self.agent.channel.name, payload["actor"])
            self.assertIn(self.user.email, payload["actor"])
            self.assertNotIn(KEY, payload["details"])
            self.assertNotIn("private@example.com", str(audit.payload))
            manual = record_audit_event(action="manual", organization=self.organization, actor=self.user)
            self.assertNotIn(KEY, manual.payload)
        self.assertEqual(json.loads(status.execute({"runId": str(run.public_id)}, "state"))["state"], "completed")

    def test_ask_edit_by_another_admin_keeps_the_original_delegate(self):
        with tenant_atomic(self.context):
            change_policy(self.context, self.agent, "native:comments.post", "ask", self.grant.revision)
            self.grant.refresh_from_db()
            self.binding = bind(self.grant, self.conversation)
            user = HumanUser.objects.create_user(email="native-approver@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="ADMIN")
            approver = TenantContext.for_membership(member)
        run = self.start()
        self.assertEqual(run.state, "approval")
        with tenant_atomic(self.context):
            step = run.steps.get()
            digest = invocation_digest(step, run)
        control(tenant=approver, public_id=run.public_id, action="edit", digest=digest)
        with tenant_atomic(self.context):
            step.refresh_from_db()
            token = step.definition["editor"]["token"]
        control(tenant=approver, public_id=run.public_id, action="revise", digest=digest,
            arguments={"conversation_id": str(self.conversation.pk), "text": "Approved edit"}, edit_token=token)
        self.execute(run)
        with tenant_atomic(self.context):
            self.assertEqual(ConversationComment.objects.get().author_id, self.user.pk)
            step.refresh_from_db()
            self.assertEqual(step.definition["approvedBy"], member.pk)
            self.assertEqual(run.definition["ai"]["delegate"], self.member.pk)

    def test_supplied_foreign_conversation_never_changes_the_bound_scope(self):
        run = self.start(arguments={"conversation_id": str(self.foreign_conversation.pk), "text": "Blocked"})
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "failed")
            self.assertFalse(ConversationComment.objects.filter(organization=self.organization).exists())
