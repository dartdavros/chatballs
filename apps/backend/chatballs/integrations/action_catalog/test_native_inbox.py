"""Inbox actions retain visibility and protected participant history in runner."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.participant_services import add_participant
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeInboxTests(CommentTransactionTestBase):
    def employee(self):
        user = HumanUser.objects.create_user(email="inbox@native.test", full_name="Inbox operator")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
        return TenantContext.for_membership(member)

    def allow(self, context, key, scope):
        ActionGrant.objects.create(organization=self.organization, membership=context.membership,
            native_key=key, operation_key="", scope=scope)

    def test_counters_and_directory_only_count_visible_conversations(self):
        context = self.employee()
        with tenant_atomic(context):
            hidden = self.make_conversation(self.organization, "hidden")
            hidden.group = EmployeeGroup.objects.create(organization=self.organization, name="Hidden")
            hidden.assigned_operator = self.author
            hidden.save(update_fields=["group", "assigned_operator"])
            self.allow(context, "conversations.counters.get", "organization")
            self.allow(context, "conversations.directory.get", "organization")
        run, counters = execute_action(context, "conversations.counters.get", {})
        self.assertEqual(run.state, "completed")
        self.assertEqual(counters["all"], 1)
        self.assertEqual(counters["groups"], [])
        run, directory = execute_action(context, "conversations.directory.get", {"q": self.author.email})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["id"] for row in directory["employees"]], [self.author.pk])
        self.assertEqual(directory["employees"][0]["openDialogs"], 0)

    def test_activity_and_journal_keep_the_same_internal_join_reason(self):
        context = self.employee()
        with tenant_atomic(self.context):
            add_participant(context=self.context, conversation_id=self.conversation.pk,
                membership_id=context.membership.pk, reason="Private consultation")
        for key in ("conversations.activity.get", "conversations.participation_journal.get"):
            run, output = execute_action(self.context, key, {"kind": "participants"},
                conversation_id=self.conversation.pk)
            self.assertEqual(run.state, "completed")
            self.assertIn("Private consultation", str(output))
            run, _ = execute_action(self.context, key,
                {"conversation_id": str(self.foreign_conversation.pk)}, conversation_id=self.conversation.pk)
            self.assertEqual(run.state, "failed")
        run, output = execute_action(self.context, "conversations.visitor_state.get", {},
            conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual(output, {"sessions": []})
