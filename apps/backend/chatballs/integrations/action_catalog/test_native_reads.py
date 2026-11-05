"""Read actions preserve visibility, public audience and personal read markers."""

from uuid import uuid4

from chatballs.conversations.comment_services import create_comment
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.models import ConversationRead, Message
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.tenancy.database import tenant_atomic


class NativeReadTests(CommentTransactionTestBase):
    def test_message_window_excludes_internal_comments_and_marks_only_the_reader(self):
        with tenant_atomic(self.context):
            message = Message.objects.create(conversation=self.conversation, author_type="CONTACT", text="Public reply")
            create_comment(context=self.context, conversation_id=self.conversation.pk,
                audience="INTERNAL", text="Internal discussion", operation_id=uuid4())
        run, output = execute_action(self.context, "messages.get", {"limit": 1}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["id"] for row in output["items"]], [message.pk])
        self.assertNotIn("Internal discussion", str(output))
        run, _ = execute_action(self.context, "conversations.detail.get", {}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            self.assertEqual(ConversationRead.objects.get(conversation=self.conversation,
                user=self.author).last_read_message_id, message.pk)

    def test_list_and_foreign_id_keep_the_original_tenant_boundary(self):
        run, output = execute_action(self.context, "conversations.get", {})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["id"] for row in output["items"]], [self.conversation.pk])
        run, _ = execute_action(self.context, "conversations.detail.get",
            {"conversation_id": str(self.foreign_conversation.pk)}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "failed")
