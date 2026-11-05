"""Mixed native/service blocks and native result references use one interpreter."""

from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.comment_test_base import CommentTestBase
from chatballs.conversations.models import ConversationLabel
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.control import control
from chatballs.tenancy.database import tenant_atomic


class NativeCompositionTests(CompositionCase):
    @staticmethod
    def native(sid, operation, **values):
        return {"id": sid, "kind": "action", "connection": "chatballs",
            "target": f"chatballs:{operation}", "inputs": {
                name: value if isinstance(value, dict) else {"source": "constant",
                    "value": str(value) if name == "conversation_id" else value}
                for name, value in values.items()}}

    def approve_and_pump(self, run):
        for _ in range(12):
            self.pump(run)
            with tenant_atomic(self.tenant):
                run.refresh_from_db()
                if run.finished_at or run.state != "approval":
                    return
                step = run.steps.get(state="approval")
                path, digest = step.path, invocation_digest(step, run)
            control(tenant=self.tenant, public_id=run.public_id,
                action="approve", path=path, digest=digest)
        self.fail("Native sequence did not finish")

    def test_service_output_binds_to_internal_comment_without_second_executor(self):
        with tenant_atomic(self.tenant):
            conversation = CommentTestBase.make_conversation(self.organization, "native-mixed")
        run = self.start([self.action("read"), self.native("note", "comments.post",
            conversation_id=conversation.pk, text={"source": "step", "step": "read", "path": "value"})],
            conversation_id=conversation.pk)
        self.approve_and_pump(run)
        with tenant_atomic(self.tenant):
            self.assertEqual(self.state(run), "completed")
            self.assertEqual(ConversationComment.objects.get().text, "HELLO")
            self.assertEqual(set(run.steps.values_list("adapter_key", flat=True)), {"independent", "chatballs"})

    def test_native_result_id_binds_to_next_native_domain_action(self):
        run = self.start([
            self.native("create", "labels.post", name="Before"),
            self.native("rename", "labels.label.patch", label_id={"source": "step", "step": "create", "path": "label.id"}, name="After"),
        ])
        self.approve_and_pump(run)
        with tenant_atomic(self.tenant):
            self.assertEqual(self.state(run), "completed")
            self.assertEqual(ConversationLabel.objects.get().name, "After")
            self.assertEqual(run.steps.filter(integration__isnull=True, state="completed").count(), 2)
