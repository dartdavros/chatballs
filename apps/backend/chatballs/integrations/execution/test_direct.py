"""Granted employee effects share snapshots, dedup and revocation checks."""

from chatballs.conversations.comment_test_base import CommentTestBase
from chatballs.integrations.execution.launch import launch_direct
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.models import ServiceConnectionSettings
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class DirectEmployeeTests(ExecutionCase):
    def setUp(self):
        super().setUp()
        self.member = self.employee.memberships.get(organization=self.organization)
        self.actor = TenantContext.for_membership(self.member)
        with tenant_atomic(self.tenant):
            self.conversation = CommentTestBase.make_conversation(self.organization, "direct")
            self.grant = ActionGrant.objects.create(organization=self.organization,
                integration=self.integration, membership=self.member,
                operation_key=self.operation.key, scope="conversation")

    def direct(self, **overrides):
        return launch_direct(**{
            "tenant": self.actor, "connection_id": self.integration.pk,
            "operation_key": self.operation.key, "trigger_key": "employee-click",
            "arguments": {"value": "private-input"}, "conversation_id": self.conversation.pk,
            "registry": self.registry, **overrides,
        })

    def queued(self):
        preview, _ = self.direct(preview=True)
        return self.direct(confirmation=preview["confirmation"])[0]

    def test_direct_employee_launch_deduplicates_and_executes_exact_snapshot(self):
        run = self.queued()
        duplicate, created = self.direct(arguments={"value": "replacement"})
        self.assertFalse(created)
        self.assertEqual(duplicate.pk, run.pk)
        with tenant_atomic(self.tenant):
            step = run.steps.get()
            key = str(step.effect_key)
            self.assertEqual(step.definition["arguments"], {"value": "private-input"})
            self.assertNotIn("private-input", step.content)
            self.assertEqual(run.initiator_id, self.member.pk)
        run_one(self.actor, run.public_id, registry=self.registry)
        run_one(self.actor, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(self.calls, [key])

    def test_missing_grant_or_context_cannot_create_direct_run(self):
        with self.assertRaisesMessage(ExecutionDenied, "context"):
            self.direct(conversation_id=None)
        with tenant_atomic(self.tenant):
            self.grant.enabled = False
            self.grant.save(update_fields=["enabled"])
        with self.assertRaisesMessage(ExecutionDenied, "permission"):
            self.direct()
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())
        self.assertEqual(self.calls, [])

    def test_grant_revoked_after_confirmation_prevents_new_effect(self):
        run = self.queued()
        with tenant_atomic(self.tenant):
            self.grant.enabled = False
            self.grant.save(update_fields=["enabled"])
        run_one(self.actor, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "failed")
        self.assertEqual(self.calls, [])

    def test_changed_adapter_contract_is_explained_without_substitution(self):
        run = self.queued()
        with tenant_atomic(self.tenant):
            ServiceConnectionSettings.objects.filter(integration=self.integration).update(adapter_version=2)
        run_one(self.actor, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "failed")
        with tenant_atomic(self.tenant):
            step = run.steps.get()
            self.assertEqual(step.error_code, "version_incompatible")
            self.assertEqual(step.adapter_version, 1)
        self.assertEqual(self.calls, [])
