"""Native STT lifecycle at controlled provider boundaries, without a provider call."""

from unittest.mock import patch

from django.core.files.base import ContentFile
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from chatballs.ai.external_agents import dispatch
from chatballs.ai.external_agents.context_testing import ContextData
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.voice import VoiceWork, run_voice
from chatballs.ai.provider.base import ProviderError
from chatballs.conversations.models import Message
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic


@override_settings(CHATBALLS_AI_PROVIDER="byok")
class ContextVoiceTests(ContextData, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.stt = Integration.objects.create(organization=self.organization, kind="SPEECH_PROVIDER",
            provider="YANDEX_SPEECHKIT", name="Native STT", secret="isolated-test-key", status="OK")
        self.agent.transcription_integration = self.stt
        self.agent.save(update_fields=["transcription_integration"])

    def voice_request(self):
        row = self.request("", kind="voice", duration_seconds=7)
        with tenant_atomic(self.context):
            row.trigger.audio.save("isolated-voice.ogg", ContentFile(b"isolated-test-audio"))
        def cleanup():
            with tenant_atomic(self.context):
                row.trigger.audio.delete(save=False)
        self.addCleanup(cleanup)
        return row

    def test_stt_once_outside_transaction_then_http_retry_uses_saved_transcript(self):
        row = self.voice_request()

        def transcribe(*args, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            return "Saved transcript"

        self.transport.return_value = None
        with patch("chatballs.speech.providers.yandex_stt.YandexSTT.transcribe", side_effect=transcribe) as stt, \
                patch("chatballs.ai.external_agents.recovery.cancel_due"):
            dispatch.run(self.context, self.conversation.pk)
            self.assertEqual(stt.call_count, 1)
            data = self.frozen(row)
            self.assertEqual(data["trigger"], {"messageId": str(row.trigger_id),
                "createdAt": row.trigger.created_at.isoformat().replace("+00:00", "Z"),
                "type": "text", "text": "Saved transcript", "wasVoice": True, "attachments": [],
                "source": {"kind": "voice", "durationSeconds": 7}})
            frozen = row.snapshot_ciphertext, row.snapshot_digest
            ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
            dispatch.run(self.context, self.conversation.pk)
            self.assertEqual(stt.call_count, 1)
            row.refresh_from_db()
            self.assertEqual((row.snapshot_ciphertext, row.snapshot_digest), frozen)
            row.trigger.refresh_from_db()
            self.assertEqual(row.trigger.transcript, "Saved transcript")
            self.assertNotIn("audio", str(data))

    def test_missing_explicit_stt_does_not_inherit_builtin_llm_and_hands_off(self):
        self.agent.transcription_integration = None
        self.agent.provider_integration = self.stt
        self.agent.save(update_fields=["transcription_integration", "provider_integration"])
        row = self.voice_request()
        with patch("chatballs.speech.providers.yandex_stt.YandexSTT.transcribe") as stt:
            self.assertIsNone(self.claim())
            stt.assert_not_called()
        row.refresh_from_db()
        self.assertEqual((row.reason_code, row.attempts), ("history_content_unavailable", 0))
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.control_mode, "PAUSED")

    def test_provider_failure_hands_off_without_sending_audio_or_inventing_text(self):
        row = self.voice_request()
        with patch("chatballs.speech.providers.yandex_stt.YandexSTT.transcribe", side_effect=ProviderError("test failure")):
            dispatch.run(self.context, self.conversation.pk)
        row.refresh_from_db()
        self.assertEqual((row.reason_code, row.attempts), ("history_content_unavailable", 0))
        self.assertEqual(row.snapshot_ciphertext, "")
        row.trigger.refresh_from_db()
        self.assertEqual(row.trigger.transcript_status, "FAILED")

    def test_restart_after_stt_checkpoint_hands_off_without_retranscribing(self):
        row = self.voice_request()
        work = self.claim()
        self.assertIsInstance(work, VoiceWork)
        ExternalAgentRequest.objects.filter(pk=row.pk).update(lease_until=timezone.now())
        self.assertIsNone(self.claim())
        self.assertFalse(run_voice(work, self.context))
        row.refresh_from_db()
        self.assertEqual(row.attempts, 0)
        self.assertEqual(row.state, "cancelled")

    def test_control_revocation_before_stt_prevents_provider_call(self):
        self.voice_request()
        work = self.claim()
        self.conversation.control_mode = "HUMAN"
        self.conversation.save(update_fields=["control_mode"])
        with patch("chatballs.speech.providers.yandex_stt.YandexSTT.transcribe") as stt:
            self.assertFalse(run_voice(work, self.context))
            stt.assert_not_called()

    def test_historical_voice_requires_saved_transcript_without_running_stt(self):
        prior = Message.objects.create(conversation=self.conversation, author_type="CONTACT", kind="voice",
                                       transcript="", duration_seconds=3)
        row = self.request()
        with patch("chatballs.speech.providers.yandex_stt.YandexSTT.transcribe") as stt:
            self.assertIsNone(self.claim())
            stt.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.reason_code, "history_content_unavailable")
        self.conversation.control_mode = "AI"
        self.conversation.save(update_fields=["control_mode"])
        prior.transcript, prior.transcript_status = "Historical transcript", "READY"
        prior.save(update_fields=["transcript", "transcript_status"])
        next_row = self.request("fresh")
        self.assertIsNotNone(self.claim())
        item = self.frozen(next_row)["context"]["history"]["messages"][0]
        self.assertEqual(item["content"]["text"], "Historical transcript")
        self.assertTrue(item["wasVoice"])
        self.assertEqual(item["source"]["durationSeconds"], 3)
