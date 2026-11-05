"""Link mutations use canonical visible conversations and optimistic revisions."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied, NativeContext
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.tenancy.database import tenant_atomic


class NativeEntityLinkTests(CommentTransactionTestBase):
    def test_visible_links_unlink_revision_and_canonical_scope(self):
        with tenant_atomic(self.context):
            connection = Integration.objects.create(organization=self.organization, name="CRM", kind="SERVICE", provider="ADAPTER")
            ServiceConnectionSettings.objects.create(organization=self.organization, integration=connection,
                adapter_key="bitrix24", adapter_version=1, auth_method="webhook")
            linked = EntityLink.objects.create(organization=self.organization, integration=connection,
                internal_kind="contact", internal_id=self.conversation.contact_id, external_kind="contact", external_id="42")
        values = {"conversation": self.conversation.pk}
        run, result = execute_action(self.context, "entity_links.get", values, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        self.assertEqual(result["items"][0]["id"], linked.pk)
        command = {**values, "pk": linked.pk, "action": "unlink", "revision": linked.revision + 1}
        run, _ = execute_action(self.context, "entity_links.command.post", command, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "failed")
        command["revision"] = linked.revision
        constrained = NativeContext(self.context, "scope-check", "run", "step", scope="conversation",
            conversation_id=self.foreign_conversation.pk)
        with self.assertRaises(NativeAccessDenied):
            native_action("entity_links.command.post").execute(constrained, command)
        run, result = execute_action(self.context, "entity_links.command.post", command, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        self.assertTrue(result["updated"])
        with tenant_atomic(self.context):
            linked.refresh_from_db()
            self.assertFalse(linked.active)
            self.assertEqual(linked.revision, command["revision"] + 1)
