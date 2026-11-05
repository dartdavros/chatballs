"""Contact actions retain owner-only merges, tenant checks and receipts."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.models import ContactMerge, Conversation
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeContactTests(CommentTransactionTestBase):
    def test_merge_and_revert_use_domain_history_and_do_not_repeat_a_completed_effect(self):
        with tenant_atomic(self.context):
            source_conversation = self.make_conversation(self.organization, "source")
            source_id = source_conversation.contact_id
        run, output = execute_action(self.context, "contacts.merge.post", {
            "contact_id": self.conversation.contact_id, "sourceId": source_id, "reason": "Same customer confirmed"})
        self.assertEqual(run.state, "completed")
        merge_id = output["client"]["merges"][0]["id"]
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(ContactMerge.objects.filter(organization=self.organization).count(), 1)
            self.assertEqual(Conversation.objects.get(pk=source_conversation.pk).contact_id, self.conversation.contact_id)
        run, _ = execute_action(self.context, "contacts.merge.delete", {
            "contact_id": self.conversation.contact_id, "mergeId": merge_id, "reason": "Separate customer confirmed"})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            self.assertEqual(Conversation.objects.get(pk=source_conversation.pk).contact_id, source_id)
            self.assertIsNotNone(ContactMerge.objects.get(pk=merge_id).reverted_at)

    def test_admin_cannot_merge_and_owner_cannot_merge_a_foreign_contact(self):
        user = HumanUser.objects.create_user(email="admin@native-contacts.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="ADMIN")
        with tenant_atomic(self.context):
            source = self.make_conversation(self.organization, "source")
        run, _ = execute_action(TenantContext.for_membership(member), "contacts.merge.post", {
            "contact_id": self.conversation.contact_id, "sourceId": source.contact_id, "reason": "Same customer confirmed"})
        self.assertEqual(run.state, "failed")
        run, _ = execute_action(self.context, "contacts.merge.post", {
            "contact_id": self.conversation.contact_id, "sourceId": self.foreign_conversation.contact_id,
            "reason": "Same customer confirmed"})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(ContactMerge.objects.filter(organization=self.organization).exists())
