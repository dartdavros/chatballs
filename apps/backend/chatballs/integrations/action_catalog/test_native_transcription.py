"""Transcription guards and stored outcomes use real domain files and runner."""

from django.core.files.base import ContentFile

from chatballs.conversations.models import Conversation, Message, MessageKind, TranscriptStatus
from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.database import tenant_atomic


class NativeTranscriptionTests(NativeFileCase):
    def voice(self, **changes):
        with tenant_atomic(self.context):
            message = Message.objects.create(conversation=self.conversation, author_type="CONTACT",
                kind=MessageKind.VOICE, audio_content_type="audio/ogg", **changes)
            message.audio.save("voice.ogg", ContentFile(b"OggS"))
            return message

    def test_ready_transcript_returns_the_original_message_without_another_provider_request(self):
        message = self.voice(transcript="Existing transcript", transcript_status=TranscriptStatus.READY)
        run, data = execute_action(self.context, "messages.transcription.post", {"message_id": message.pk},
            conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        self.assertEqual((data["message"]["id"], data["message"]["transcript"], data["message"]["transcriptStatus"]),
            (message.pk, "Existing transcript", "READY"))
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            message.refresh_from_db()
            self.assertEqual(message.transcript, "Existing transcript")

    def test_unconfigured_provider_is_a_definitive_failure_and_keeps_the_original_failed_status(self):
        message = self.voice()
        run, _data = execute_action(self.context, "messages.transcription.post", {"message_id": message.pk},
            conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            message.refresh_from_db()
            self.assertEqual(message.transcript_status, TranscriptStatus.FAILED)
            self.assertEqual(message.transcript, "")

    def test_canonical_conversation_and_voice_kind_are_checked_before_transcription(self):
        message = self.voice(transcript_status=TranscriptStatus.READY, transcript="Private transcript")
        with tenant_atomic(self.context):
            other = Conversation.objects.create(organization=self.organization, channel=self.conversation.channel,
                connection=self.connection, contact=self.conversation.contact, group=self.group)
            text = Message.objects.create(conversation=self.conversation, author_type="CONTACT", text="Text")
        for target, conversation in ((message.pk, other.pk), (text.pk, self.conversation.pk)):
            run, data = execute_action(self.context, "messages.transcription.post", {"message_id": target},
                conversation_id=conversation)
            self.assertEqual(run.state, "failed")
            self.assertIsNone(data)
