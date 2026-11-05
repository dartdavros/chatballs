"""Current delegate authority and PostgreSQL tenant guards cannot be bypassed."""

from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from chatballs.conversations.comment_models import ConversationComment
from chatballs.integrations.execution.agent_actions import catalog, change_policy
from chatballs.integrations.execution.ai_policy import bind
from chatballs.integrations.execution.ai_reply import allowed
from chatballs.integrations.execution.native_ai_testing import NativeAICase
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.tenancy.database import tenant_atomic


class NativeAIPolicyTests(NativeAICase):
    def assert_no_effect(self, run):
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "failed")
            self.assertFalse(ConversationComment.objects.filter(organization=self.organization).exists())

    def test_catalog_and_unchanged_mode_do_not_backfill_a_legacy_delegate(self):
        with tenant_atomic(self.context):
            self.grant.delegate = None
            self.grant.save(update_fields=["delegate"])
            catalog(self.organization.pk, self.agent)
            change_policy(self.context, self.agent, "native:comments.post", "self", self.grant.revision)
            self.grant.refresh_from_db()
            self.assertIsNone(self.grant.delegate_id)
            self.binding = bind(self.grant, self.conversation)
        self.assertEqual(self.tools(), [])
        with self.assertRaises(ExecutionDenied):
            self.start()
        with tenant_atomic(self.context):
            change_policy(self.context, self.agent, "native:comments.post", "off", self.grant.revision)
            self.grant.refresh_from_db()
            change_policy(self.context, self.agent, "native:comments.post", "self", self.grant.revision)
            self.grant.refresh_from_db()
            self.assertEqual(self.grant.delegate_id, self.member.pk)

    def test_blocked_delegate_denies_effect_status_and_final_reply(self):
        _, status = self.tools()
        run = self.start()
        with tenant_atomic(self.context):
            self.member.blocked_at = timezone.now()
            self.member.save(update_fields=["blocked_at"])
            self.assertFalse(allowed(self.context, self.conversation.pk, [run.public_id]))
        with self.assertRaises(ExecutionDenied):
            status.execute({"runId": str(run.public_id)}, "state")
        self.assert_no_effect(run)

    def test_demoted_delegate_cannot_keep_native_authority(self):
        run = self.start()
        with tenant_atomic(self.context):
            self.member.role = "EMPLOYEE"
            self.member.save(update_fields=["role"])
        self.assert_no_effect(run)

    def test_inactive_delegate_user_cannot_keep_native_authority(self):
        run = self.start()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assert_no_effect(run)

    def test_retargeted_exact_native_key_cannot_authorize_old_snapshot(self):
        run = self.start()
        with tenant_atomic(self.context):
            # Even an unchanged revision cannot turn another target into authority.
            AgentActionGrant.objects.filter(pk=self.grant.pk).update(native_key="comments.get")
        self.assert_no_effect(run)

    def test_delegate_binding_cannot_be_replaced_under_a_queued_run(self):
        run = self.start()
        with tenant_atomic(self.context):
            AgentActionGrant.objects.filter(pk=self.grant.pk).update(delegate=None)
        self.assert_no_effect(run)

    def test_native_grant_is_unique_and_delegate_is_checked_by_postgresql(self):
        with tenant_atomic(self.context):
            with self.assertRaises(DatabaseError), transaction.atomic():
                AgentActionGrant.objects.bulk_create([AgentActionGrant(organization=self.organization,
                    agent=self.agent, native_key="comments.post", mode="self")])
            with self.assertRaisesMessage(DatabaseError, "cross-tenant relation"), transaction.atomic():
                AgentActionGrant.objects.filter(pk=self.grant.pk).update(delegate_id=self.foreign_member.pk)
            with self.assertRaises(DatabaseError), transaction.atomic():
                AgentActionGrant.objects.filter(pk=self.grant.pk).update(operation_key="another-target")
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            with tenant_atomic(self.foreign.pk):
                self.assertFalse(AgentActionGrant.objects.filter(pk=self.grant.pk).exists())
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")
