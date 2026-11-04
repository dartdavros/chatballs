"""Agent grants exercise the actual PostgreSQL launch/runner boundaries."""

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from chatballs.ai.models import AIAgent
from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation
from chatballs.events.models import OutboxEvent
from chatballs.integrations.execution.ai_bridge import plan_actions
from chatballs.integrations.execution.ai_launch import launch_ai
from chatballs.integrations.execution.ai_policy import bind
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class AgentExecutionCase(ExecutionCase):
    def setUp(self):
        super().setUp()
        with tenant_atomic(self.tenant):
            provider = Integration.objects.create(organization=self.organization, name="Provider",
                kind="LLM_PROVIDER", provider="DEMO", secret="test-provider", is_active=True)
            self.channel = Channel.objects.create(organization=self.organization, name="Agent", code="execution-agent")
            self.agent = AIAgent.objects.create(channel=self.channel, provider_integration=provider, status="ACTIVE", model="test")
            contact = Contact.objects.create(organization=self.organization, name="Client")
            self.conversation = Conversation.objects.create(organization=self.organization, channel=self.channel, contact=contact)
            self.grant = AgentActionGrant.objects.create(agent=self.agent, integration=self.integration,
                operation_key=self.operation.key, mode="self")
            self.binding = bind(self.grant, self.conversation)

    def start(self, *, preview=False, key="call-1"):
        return launch_ai(self.tenant, self.binding, {"value": "private-input"}, key,
                         registry=self.registry, preview=preview)

    def ask(self):
        with tenant_atomic(self.tenant):
            self.grant.mode = "ask"
            self.grant.save()
            self.binding = bind(self.grant, self.conversation)
        return self.start()

    def approve(self, run):
        with tenant_atomic(self.tenant):
            digest = invocation_digest(run.steps.get(), run)
        return control(tenant=self.tenant, public_id=run.public_id, action="approve", digest=digest)

class AgentExecutionTests(AgentExecutionCase):
    def test_explicit_write_grant_uses_shared_runner_without_blanket_confirmation(self):
        run = self.start()
        self.assertEqual(run.state, "queued")
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(self.calls), 1)

    def test_catalog_requires_grants_and_never_migrates_legacy_permissions(self):
        with tenant_atomic(self.tenant), patch("chatballs.integrations.execution.ai_bridge.cached_tool_support", return_value=True):
            self.assertEqual(len(plan_actions(self.agent, self.conversation, registry=self.registry)), 2)
            reserved = {f"chatballs_action_{self.grant.pk}", "chatballs_action_status"}
            tools = plan_actions(self.agent, self.conversation, registry=self.registry, reserved_names=reserved)
            self.assertFalse(reserved & {tool.spec.name for tool in tools})
            self.grant.delete()
            self.assertEqual(plan_actions(self.agent, self.conversation, registry=self.registry), [])

    def test_preview_validates_without_runs_or_outbox(self):
        result = self.start(preview=True)
        self.assertIn("arguments", result)
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())
            self.assertFalse(OutboxEvent.objects.filter(event_type="integrations.run").exists())

    def test_revocation_between_launch_and_effect(self):
        run = self.start()
        with tenant_atomic(self.tenant):
            self.grant.mode = "off"
            self.grant.save()
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.state(run), "failed")

    def test_takeover_and_return_cannot_revive_an_old_run(self):
        run = self.start()
        with tenant_atomic(self.tenant):
            self.conversation.control_mode = "HUMAN"
            self.conversation.save(update_fields=["control_mode"])
            self.conversation.control_mode = "AI"
            self.conversation.save(update_fields=["control_mode"])
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.calls, [])

    def test_mode_generation_is_rechecked(self):
        run = self.start()
        with tenant_atomic(self.tenant):
            self.organization.operation_mode_version += 1
            self.organization.save(update_fields=["operation_mode_version"])
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.calls, [])

    def test_agent_configuration_change_blocks_effect_and_late_result(self):
        run = self.start()
        with tenant_atomic(self.tenant):
            self.agent.model = "different-model"
            self.agent.save(update_fields=["model"])
            from chatballs.integrations.execution.ai_reply import allowed
            self.assertFalse(allowed(self.tenant, self.conversation.pk, [run.public_id]))
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.calls, [])

    def test_ask_requires_human_and_current_exact_digest(self):
        run = self.ask()
        self.assertEqual(run.state, "approval")
        with tenant_atomic(self.tenant):
            step = run.steps.get()
            old = invocation_digest(step, run)
            step.definition = {"arguments": {"value": "new-value"}}
            step.save()
        with self.assertRaises(ExecutionDenied):
            control(tenant=self.tenant, public_id=run.public_id, action="approve", digest=old)
        self.approve(run)
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(len(self.calls), 1)

    def test_expired_request_cannot_be_approved(self):
        run = self.ask()
        with tenant_atomic(self.tenant):
            data = run.definition
            data["ai"]["approvalDeadline"] = (timezone.now() - timedelta(seconds=1)).isoformat()
            run.definition = data
            run.save()
        with self.assertRaises(ExecutionDenied):
            self.approve(run)

    def test_approver_revocation_is_rechecked_before_effect(self):
        run = self.ask()
        self.approve(run)
        with tenant_atomic(self.tenant):
            self.tenant.membership.blocked_at = timezone.now()
            self.tenant.membership.save(update_fields=["blocked_at"])
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.calls, [])
