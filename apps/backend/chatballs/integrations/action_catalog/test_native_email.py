"""Mail actions use the actual domain queue, permissions and immutable route."""

import io
import tempfile
from pathlib import Path

from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from chatballs.conversations.email_attempt_models import EmailSendAttempt, EmailSendOperation
from chatballs.conversations.email_continuation_test_base import EmailContinuationTestBase
from chatballs.conversations.email_workflow_test_base import EmailWorkflowTestBase
from chatballs.conversations.models import Conversation
from chatballs.conversations.selectors import conversation_messages
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.files import store_service_file
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeEmailTests(TransactionTestCase):
    make_member = staticmethod(EmailContinuationTestBase.make_member)
    make_connection = staticmethod(EmailContinuationTestBase.make_connection)
    send = EmailWorkflowTestBase.send
    url = EmailWorkflowTestBase.url

    def setUp(self):
        EmailContinuationTestBase.setUpTestData.__func__(type(self))
        EmailWorkflowTestBase.setUp(self)
        media = tempfile.TemporaryDirectory(prefix=".test-native-email-", dir=Path(__file__).resolve().parents[3])
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))
        with tenant_atomic(self.context):
            for key in ("email_options.get", "email_operations.get", "email_operations.post", "email_retry.post"):
                ActionGrant.objects.create(organization=self.organization, membership=self.member,
                    native_key=f"messages.{key}", scope="conversation")

    def execute(self, key, values=None, *, conversation=None, tenant=None):
        return execute_action(tenant or self.context, f"messages.{key}", values or {},
            conversation_id=(conversation or self.conversation).pk)

    def send_values(self, **changes):
        return {"recipient": self.contact.email, "connectionId": self.mailbox.pk,
                "text": "Mail queued through the common runner", "subject": "Enquiry", **changes}

    def test_read_actions_share_visible_api_results_without_connection_secrets(self):
        run, data = self.execute("email_options.get")
        self.assertEqual(run.state, "completed")
        self.assertEqual(data, self.client.get(self.url("email/options/")).json())
        self.assertNotIn(self.mailbox.secret, str(data))
        operation = self.send()
        run, data = self.execute("email_operations.get", {"messageIds": [operation.letter.message_id]})
        self.assertEqual(run.state, "completed")
        self.assertEqual(data, self.client.get(self.url("email/operations/") + f"?messageIds={operation.letter.message_id}").json())
        run, data = self.execute("email_operations.get", {"messageIds": []})
        self.assertEqual(data, {"items": [], "nextCursor": None})

    def test_send_file_queues_once_with_factual_state_and_preserves_original_audience(self):
        file = store_service_file(context=self.context, integration=None, name="receipt.pdf", content_type="application/pdf",
            stream=io.BytesIO(b"%PDF-1.4"), size=8)
        # A manager may select an independent organization file in the public API.
        with tenant_atomic(self.context):
            self.member.role = "ADMIN"
            self.member.save(update_fields=["role"])
        run, data = self.execute("email_operations.post", self.send_values(file={"fileId": file.file_id}))
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        self.assertFalse(data["operation"]["deliveryConfirmed"])
        self.assertEqual(data["operation"]["attempts"][0]["state"], "PENDING")
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            operation = EmailSendOperation.objects.get()
            self.assertEqual(operation.client_key, str(run.steps.get().effect_key))
            self.assertEqual(operation.attempts.count(), 1)
            self.assertEqual(operation.letter.message.kind, "file")
            self.assertEqual(operation.letter.message.attachment_size, 8)
            self.assertTrue(conversation_messages(self.conversation).filter(pk=operation.letter.message_id).exists())
            self.assertEqual(operation.letter.thread.recipient, self.contact.email)
            self.assertEqual(self.conversation.domain_events.filter(event_type="PUBLIC_REPLY").count(), 1)
            self.assertEqual(operation.attempts.get().outbox_event.event_type, "conversations.email_send_requested")

    def test_send_keeps_saved_recipient_tenant_assignment_and_canonical_context_guards(self):
        for changes in ({"recipient": "unsaved@example.test"}, {"connectionId": self.foreign_mailbox.pk}):
            run, _data = self.execute("email_operations.post", self.send_values(**changes))
            self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            other = Conversation.objects.create(organization=self.organization, channel=self.channel,
                connection=self.web, contact=self.contact, assigned_operator=self.member.user, control_mode="HUMAN")
        run, _data = self.execute("email_operations.post", self.send_values(conversation_id=str(other.pk)))
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            colleague = self.make_member(self.organization, "assigned-other@mail-data.test")
            Conversation.objects.filter(pk=self.conversation.pk).update(assigned_operator=colleague.user)
        with self.assertRaises(ExecutionDenied):
            self.execute("email_operations.post", self.send_values())
        with tenant_atomic(self.context):
            self.assertFalse(EmailSendOperation.objects.exists())

    def test_unknown_retry_requires_acknowledgement_and_replays_the_same_attempt(self):
        operation = self.send()
        with tenant_atomic(self.context):
            now = timezone.now()
            EmailSendAttempt.objects.filter(operation=operation).update(state="UNKNOWN", error_code="TRANSPORT_ERROR",
                started_at=now, finished_at=now)
        run, _data = self.execute("email_retry.post", {"operation_id": operation.pk})
        self.assertEqual(run.state, "failed")
        run, data = self.execute("email_retry.post", {"operation_id": operation.pk, "acknowledgeUnknown": True})
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        self.assertEqual((data["attempt"]["number"], data["attempt"]["state"]), (2, "PENDING"))
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(operation.attempts.count(), 2)
        foreign = TenantContext.for_membership(self.foreign_member)
        with self.assertRaises(ExecutionDenied):
            self.execute("email_retry.post", {"operation_id": operation.pk}, tenant=foreign)
