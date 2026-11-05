"""Real WEB replies, source restrictions, delivery uncertainty and common runner."""

import io
from unittest.mock import patch

from django.utils import timezone

from chatballs.ai.assistance_send_models import ReplySuggestionSend
from chatballs.ai.models import (
    AIAgent,
    ReplyAssistanceAttempt,
    ReplySuggestion,
)
from chatballs.conversations import transports
from chatballs.conversations.models import Message
from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.files import store_service_file
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.database import tenant_atomic


class NativeMessageTests(NativeFileCase):
    def execute(self, key, arguments=None):
        return execute_action(self.context, key, arguments or {}, conversation_id=self.conversation.pk)

    def file(self, name="reply.txt", content_type="text/plain", content=b"Customer attachment"):
        file = store_service_file(context=self.context, integration=None, name=name,
            content_type=content_type, stream=io.BytesIO(content), size=len(content))
        return {"fileId": file.file_id}

    def assert_reply(self, run, result, kind):
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        self.assertEqual(result["message"]["kind"], kind)
        self.assertTrue(result["published"])
        self.assertTrue(result["transportAccepted"])
        self.assertFalse(result["deliveryConfirmed"])
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(Message.objects.exclude(author_type="SYSTEM").count(), 1)
            message = Message.objects.exclude(author_type="SYSTEM").get()
            self.assertEqual(message.author_user_id, self.user.pk)
            self.assertEqual(self.conversation.domain_events.filter(event_type="PUBLIC_REPLY").count(), 1)
            self.conversation.refresh_from_db()
            return message

    def test_text_uses_the_original_claim_and_public_reply_once(self):
        run, result = self.execute("messages.post", {"text": "Source service reply"})
        message = self.assert_reply(run, result, "")
        self.assertEqual(message.text, "Source service reply")
        self.assertEqual(self.conversation.control_mode, "HUMAN")
        self.assertEqual(self.conversation.assigned_operator_id, self.user.pk)

    def test_contact_request_keeps_web_audience_and_cannot_replace_a_saved_phone(self):
        run, result = self.execute("messages.request_contact.post")
        self.assert_reply(run, result, "contact_request")
        with tenant_atomic(self.context):
            contact = self.conversation.contact
            contact.phone = "+79991234567"
            contact.save(update_fields=["phone"])
        refused, result = self.execute("messages.request_contact.post")
        self.assertEqual(refused.state, "failed")
        self.assertIsNone(result)
        with tenant_atomic(self.context):
            self.assertEqual(Message.objects.exclude(author_type="SYSTEM").count(), 1)

    def test_attachment_uses_normal_file_reference_and_source_storage(self):
        run, result = self.execute("messages.attachment.post", {"file": self.file(), "text": "Attachment caption"})
        message = self.assert_reply(run, result, "file")
        with tenant_atomic(self.context):
            self.assertEqual(message.attachment_name, "reply.txt")
            with message.attachment.open("rb") as handle:
                self.assertEqual(handle.read(), b"Customer attachment")

    def test_voice_preserves_audio_and_duration_without_claiming_customer_delivery(self):
        run, result = self.execute("messages.voice.post",
            {"audio": self.file("voice.ogg", "audio/ogg", b"OggS"), "duration": 3})
        message = self.assert_reply(run, result, "voice")
        self.assertEqual((message.duration_seconds, message.audio_content_type), (3, "audio/ogg"))

    def test_source_file_and_voice_rejections_do_not_publish_or_claim(self):
        with tenant_atomic(self.context):
            before = self.conversation.control_mode
            self.connection.voice_messages_enabled = False
            self.connection.save(update_fields=["voice_messages_enabled"])
        for key, values in (("messages.attachment.post", {"file": self.file("blocked.exe")}),
                            ("messages.voice.post", {"audio": self.file("voice.ogg", "audio/ogg", b"OggS")})):
            run, _result = self.execute(key, values)
            self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(Message.objects.exists())
            self.conversation.refresh_from_db()
            self.assertEqual(self.conversation.control_mode, before)

    def test_transport_refusal_is_unknown_and_recovery_does_not_send_again(self):
        # Fault injection into the existing transport dispatch, not a mock API
        # or a substituted environment. No real provider access is claimed.
        with patch.dict(transports._SEND, {"WEB": lambda *_args, **_kwargs: False}):
            run, result = self.execute("messages.post", {"text": "Unconfirmed transport"})
        self.assertEqual(run.state, "unknown")
        self.assertIsNone(result)
        control(tenant=self.context, public_id=run.public_id, action="reconcile")
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "unknown")
            self.assertEqual(Message.objects.exclude(author_type="SYSTEM").count(), 1)
        # The observation is local to its invocation and does not leak.
        next_run, result = self.execute("messages.post", {"text": "Another explicit reply"})
        self.assertEqual(next_run.state, "completed")
        self.assertTrue(result["transportAccepted"])

    def test_ready_suggestion_sends_at_commit_and_preserves_immutable_source(self):
        with tenant_atomic(self.context):
            agent = AIAgent.objects.create(channel=self.conversation.channel, name="Reply assistant")
            attempt = ReplyAssistanceAttempt.objects.create(organization=self.organization,
                conversation=self.conversation, agent=agent, requested_by=self.member,
                operation_key="ready-attempt", history_version="history-v1")
            suggestion = ReplySuggestion.objects.create(organization=self.organization,
                attempt=attempt, requested_by=self.member, operation_key="ready-suggestion",
                history_version="history-v1", position=1)
            now = timezone.now()
            ReplyAssistanceAttempt.objects.filter(pk=attempt.pk).update(
                status="READY", started_at=now, completed_at=now)
            ReplySuggestion.objects.filter(pk=suggestion.pk).update(status="READY",
                started_at=now, completed_at=now, original_text="Immutable source draft")
        run, result = self.execute("messages.post",
            {"suggestionId": str(suggestion.public_id), "text": "Edited employee reply"})
        message = self.assert_reply(run, result, "")
        self.assertEqual(message.text, "Edited employee reply")
        with tenant_atomic(self.context):
            suggestion.refresh_from_db()
            self.assertEqual(suggestion.original_text, "Immutable source draft")
            self.assertEqual(ReplySuggestionSend.objects.get().operation_key, str(run.steps.get().effect_key))
        refused, _ = self.execute("messages.post",
            {"suggestionId": str(suggestion.public_id), "text": "Another reply"})
        self.assertEqual(refused.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(ReplySuggestionSend.objects.count(), 1)
