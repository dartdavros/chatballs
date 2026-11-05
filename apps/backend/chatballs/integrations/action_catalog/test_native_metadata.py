"""Metadata actions retain tenant, original role and source field validation."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeMetadataTests(CommentTransactionTestBase):
    def test_contact_validation_and_edit_preserve_domain_behavior(self):
        run, _ = execute_action(self.context, "contacts.from_conversation.post",
            {"email": "broken"}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "failed")
        run, output = execute_action(self.context, "contacts.from_conversation.post",
            {"name": "Updated customer", "email": "USER@example.test"}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["conversation"]["contact"]["name"], "Updated customer")
        with tenant_atomic(self.context):
            self.conversation.contact.refresh_from_db()
            self.assertEqual(self.conversation.contact.email, "user@example.test")

    def test_employee_grant_does_not_allow_restoring_an_archive(self):
        user = HumanUser.objects.create_user(email="metadata@native.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
        tenant = TenantContext.for_membership(member)
        with tenant_atomic(self.context):
            self.conversation.assigned_operator = user
            self.conversation.control_mode = "HUMAN"
            self.conversation.save(update_fields=["assigned_operator", "control_mode"])
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="conversations.archive.post", operation_key="", scope="conversation")
        run, _ = execute_action(tenant, "conversations.archive.post", {"archived": True},
            conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        with self.assertRaises(ExecutionDenied):
            execute_action(tenant, "conversations.archive.post", {"archived": False},
                conversation_id=self.conversation.pk)
        with tenant_atomic(self.context):
            self.conversation.refresh_from_db()
            self.assertIsNotNone(self.conversation.archived_at)

    def test_foreign_label_rejects_the_entire_replacement(self):
        from chatballs.conversations.models import ConversationLabel
        with tenant_atomic(self.context):
            original = ConversationLabel.objects.create(organization=self.organization, name="Original")
            self.conversation.labels.add(original)
        with tenant_atomic(self.foreign.pk):
            foreign = ConversationLabel.objects.create(organization=self.foreign, name="Foreign")
        run, _ = execute_action(self.context, "conversations.labels.post", {"labelIds": [foreign.pk]},
            conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(list(self.conversation.labels.values_list("pk", flat=True)), [original.pk])
