from unittest import mock

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.channels.models import Channel
from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import (
    Contact,
    ControlMode,
    Conversation,
    Message,
    MessageAuthor,
    MessageKind,
    TranscriptStatus,
)
from chatballs.conversations.transports.base import InboundMessage
from chatballs.identity.bootstrap import bootstrap_edevs_owner
from chatballs.tenancy.database import tenant_atomic
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)


class VoiceTestCase(TestCase):
    """Голосовые сообщения (дизайн-базлайн v2, кадр H): приём, отдача,
    расшифровка через BYOK, отправка оператором в Telegram и MAX."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        self.integration = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="Bot",
            secret="token",
            channel=self.channel,
        )
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def _voice_inbound(self, external_id: str = "v-1") -> InboundMessage:
        return InboundMessage(
            external_id=external_id,
            user_id="u-1",
            chat_id="c-1",
            text="",
            display_name="Ольга",
            voice_file_id="file-123",
            voice_duration=14,
            voice_mime="audio/ogg",
        )


class VoiceIngestTests(VoiceTestCase):
    def test_inbound_voice_is_stored_and_queued_for_operator(self) -> None:
        with mock.patch(
            "chatballs.conversations.ingest.transports.download_voice",
            return_value=(b"OGGDATA", "audio/ogg"),
        ), tenant_atomic(self.organization.id):
            # Продовый поллер выполняет ingest в tenant-контексте БД —
            # без него storage-гард не пропустит запись файла.
            ingest_inbound(self.integration, self._voice_inbound())

        conversation = self.channel.conversations.get()
        message = conversation.messages.get(kind=MessageKind.VOICE)
        self.assertEqual(message.duration_seconds, 14)
        self.assertTrue(message.audio)
        self.assertEqual(message.transcript_status, TranscriptStatus.NONE)
        # AI голос не разбирает — диалог уходит оператору.
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)

    def test_download_failure_keeps_placeholder_message(self) -> None:
        with mock.patch(
            "chatballs.conversations.ingest.transports.download_voice",
            side_effect=ValueError("boom"),
        ), tenant_atomic(self.organization.id):
            ingest_inbound(self.integration, self._voice_inbound())

        message = self.channel.conversations.get().messages.get()
        self.assertEqual(message.kind, MessageKind.TEXT)
        self.assertIn("Голосовое сообщение", message.text)
        self.assertFalse(message.audio)


class VoiceApiTests(VoiceTestCase):
    def _voice_message(self) -> Message:
        contact = Contact.objects.create(organization=self.organization, name="Ольга")
        conversation = Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.integration,
            contact=contact,
        )
        message = Message.objects.create(
            conversation=conversation,
            author_type=MessageAuthor.CONTACT,
            kind=MessageKind.VOICE,
            audio_content_type="audio/ogg",
            duration_seconds=14,
        )
        with tenant_atomic(self.organization.id):
            message.audio.save("voice.ogg", ContentFile(b"OGGDATA"), save=False)
        message.save(update_fields=["audio"])
        return message

    def test_audio_is_served_to_visible_viewer_only(self) -> None:
        message = self._voice_message()
        response = self.client.get(
            f"/api/v1/conversations/messages/{message.id}/audio/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "audio/ogg")

        outsider = HumanUser.objects.create_user(
            email="stranger@edevs.tech", password="Password-123"
        )
        other = Organization.objects.create(name="Other", slug="voice-other")
        OrganizationMembership.objects.create(
            user=outsider,
            organization=other,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )
        foreign = APIClient()
        foreign.force_authenticate(outsider)
        denied = foreign.get(f"/api/v1/conversations/messages/{message.id}/audio/")
        self.assertEqual(denied.status_code, 404)

    def test_transcribe_uses_provider_and_persists(self) -> None:
        message = self._voice_message()
        response = self.client.post(
            f"/api/v1/conversations/messages/{message.id}/transcribe/"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["message"]
        # Тестовый провайдер отдаёт детерминированную стенограмму.
        self.assertIn("стенограмма", payload["transcript"])
        self.assertEqual(payload["transcriptStatus"], TranscriptStatus.READY)
        message.refresh_from_db()
        self.assertEqual(message.transcript_status, TranscriptStatus.READY)

        # Повтор идемпотентен: провайдер не вызывается заново.
        with mock.patch(
            "chatballs.ai.provider.local.LocalProvider.transcribe"
        ) as transcribe:
            repeat = self.client.post(
                f"/api/v1/conversations/messages/{message.id}/transcribe/"
            )
        self.assertEqual(repeat.status_code, 200)
        transcribe.assert_not_called()

    def test_operator_sends_voice_to_telegram(self) -> None:
        message = self._voice_message()
        conversation = message.conversation
        conversation.control_mode = ControlMode.HUMAN
        conversation.assigned_operator = HumanUser.objects.get(email="owner@edevs.tech")
        conversation.external_chat_id = "c-1"
        conversation.save(
            update_fields=["control_mode", "assigned_operator", "external_chat_id"]
        )

        with mock.patch(
            "chatballs.conversations.transports.send_voice", return_value=True
        ) as send:
            response = self.client.post(
                f"/api/v1/conversations/{conversation.id}/voice/",
                data={
                    "audio": SimpleUploadedFile(
                        "voice.webm", b"WEBMDATA", content_type="audio/webm"
                    ),
                    "duration": "3",
                },
                format="multipart",
            )
        self.assertEqual(response.status_code, 201)
        send.assert_called_once()
        sent = conversation.messages.get(author_type=MessageAuthor.OPERATOR)
        self.assertEqual(sent.kind, MessageKind.VOICE)
        self.assertEqual(sent.duration_seconds, 3)
        self.assertTrue(sent.audio)

    def test_max_send_voice_uploads_then_sends_attachment(self) -> None:
        from chatballs.conversations import transports
        from chatballs.conversations.transports import max as max_transport

        integration = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.MAX,
            name="MAX Bot",
            secret="max-token",
            channel=Channel.objects.create(
                organization=self.organization, code="max-line", name="MAX"
            ),
        )
        self.assertTrue(transports.supports_voice_send(integration))

        # Последовательность запросов: /uploads -> multipart -> /messages.
        with mock.patch.object(
            max_transport,
            "request_json",
            side_effect=[{"url": "https://upload.example/audio"}, {"message": {}}],
        ) as request_json, mock.patch.object(
            max_transport,
            "request_json_multipart",
            return_value={"token": "att-1"},
        ) as upload:
            sent = transports.send_voice(
                integration,
                chat_id="c-1",
                user_id="",
                content=b"WEBMDATA",
                content_type="audio/webm",
                duration=3,
            )

        self.assertTrue(sent)
        upload.assert_called_once()
        self.assertEqual(upload.call_args.args[0], "https://upload.example/audio")
        send_call = request_json.call_args_list[-1]
        self.assertIn("/messages?", send_call.args[0])
        self.assertEqual(
            send_call.kwargs["body"],
            {"attachments": [{"type": "audio", "payload": {"token": "att-1"}}]},
        )

    def test_voice_send_requires_assignment_and_supported_channel(self) -> None:
        message = self._voice_message()
        conversation = message.conversation
        conversation.external_chat_id = "c-1"
        conversation.save(update_fields=["external_chat_id"])

        # Диалог не взят — 403.
        denied = self.client.post(
            f"/api/v1/conversations/{conversation.id}/voice/",
            data={
                "audio": SimpleUploadedFile(
                    "voice.webm", b"WEBMDATA", content_type="audio/webm"
                )
            },
            format="multipart",
        )
        self.assertEqual(denied.status_code, 403)
