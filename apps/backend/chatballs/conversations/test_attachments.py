"""Файлы и фото в диалоге: приём (TG/MAX/почта/виджет), отдача, отправка оператором."""

from unittest import mock

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    ControlMode,
    Conversation,
    Message,
    MessageAuthor,
    MessageKind,
)
from chatballs.conversations.transports.base import InboundFile, InboundMessage
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import EmployeeRole, HumanUser, Organization, OrganizationMembership
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient as APIClient


class AttachmentTestCase(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.owner = HumanUser.objects.get(email="owner@example.com")
        self.channel = Channel.objects.create(organization=self.organization, code="line", name="Линия")
        self.integration = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="Bot",
            secret="token",
            channel=self.channel,
        )
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def _inbound(self, *, text: str = "", files: tuple[InboundFile, ...] = (), external_id: str = "f-1") -> InboundMessage:
        return InboundMessage(
            external_id=external_id, user_id="u-1", chat_id="c-1", text=text, display_name="Ольга", files=files
        )


class AttachmentIngestTests(AttachmentTestCase):
    def test_file_only_message_is_stored_and_queued_for_operator(self) -> None:
        inbound = self._inbound(files=(InboundFile(name="смета.pdf", content_type="application/pdf", file_id="tg-1"),))
        with mock.patch(
            "chatballs.conversations.ingest.transports.download_file", return_value=(b"%PDF", "application/pdf")
        ), tenant_atomic(self.organization.id):
            ingest_inbound(self.integration, inbound)

        conversation = self.channel.conversations.get()
        message = conversation.messages.get()
        self.assertEqual(message.kind, MessageKind.FILE)
        self.assertEqual(message.attachment_name, "смета.pdf")
        self.assertEqual(message.attachment_size, 4)
        self.assertTrue(message.attachment)
        self.assertEqual(message.external_id, "f-1")
        # AI файл не разбирает — диалог уходит оператору.
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)

    def test_caption_with_photo_keeps_text_message_and_file(self) -> None:
        inbound = self._inbound(
            text="Вот фото", files=(InboundFile(name="photo.jpg", content_type="image/jpeg", file_id="tg-2", is_image=True),)
        )
        with mock.patch(
            "chatballs.conversations.ingest.transports.download_file", return_value=(b"JPEG", "image/jpeg")
        ), tenant_atomic(self.organization.id):
            ingest_inbound(self.integration, inbound)

        messages = list(self.channel.conversations.get().messages.order_by("id"))
        self.assertEqual([m.kind for m in messages], [MessageKind.TEXT, MessageKind.FILE])
        self.assertEqual(messages[0].text, "Вот фото")
        self.assertEqual(messages[1].attachment_content_type, "image/jpeg")

    def test_download_failure_keeps_placeholder(self) -> None:
        inbound = self._inbound(files=(InboundFile(name="big.zip", file_id="tg-3"),))
        with mock.patch(
            "chatballs.conversations.ingest.transports.download_file", side_effect=ValueError("too big")
        ), tenant_atomic(self.organization.id):
            ingest_inbound(self.integration, inbound)

        message = self.channel.conversations.get().messages.get()
        self.assertEqual(message.kind, MessageKind.TEXT)
        self.assertIn("big.zip", message.text)
        self.assertFalse(message.attachment)

    def test_telegram_download_uses_get_file(self) -> None:
        from chatballs.conversations import transports

        calls: list[str] = []

        def fake_request_json(url, **kwargs):
            calls.append(url)
            return {"ok": True, "result": {"file_path": "documents/file_1.pdf"}}

        with mock.patch("chatballs.conversations.transports.telegram.request_json", fake_request_json), mock.patch(
            "chatballs.conversations.transports.telegram.download_bytes", return_value=b"%PDF"
        ) as download:
            content, content_type = transports.download_file(
                self.integration, InboundFile(name="a.pdf", content_type="application/pdf", file_id="tg-9")
            )
        self.assertEqual(content, b"%PDF")
        self.assertEqual(content_type, "application/pdf")
        self.assertIn("getFile?file_id=tg-9", calls[0])
        self.assertIn("/file/bottoken/documents/file_1.pdf", download.call_args.args[0])


class AttachmentApiTests(AttachmentTestCase):
    def _conversation(self) -> Conversation:
        contact = Contact.objects.create(organization=self.organization, name="Ольга")
        ConnectionIdentity.objects.create(contact=contact, connection=self.integration, external_user_id="u-1", display_name="Ольга")
        return Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.integration,
            contact=contact,
            external_chat_id="c-1",
        )

    def _file_message(self, conversation: Conversation | None = None) -> Message:
        conversation = conversation or self._conversation()
        message = Message.objects.create(
            conversation=conversation,
            author_type=MessageAuthor.CONTACT,
            kind=MessageKind.FILE,
            attachment_name="смета.pdf",
            attachment_content_type="application/pdf",
            attachment_size=4,
        )
        with tenant_atomic(self.organization.id):
            message.attachment.save("смета.pdf", ContentFile(b"%PDF"), save=False)
        message.save(update_fields=["attachment"])
        return message

    def test_attachment_is_served_with_name_to_visible_viewer_only(self) -> None:
        message = self._file_message()
        response = self.client.get(f"/api/v1/conversations/messages/{message.id}/attachment/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"%PDF")

        inline = self.client.get(f"/api/v1/conversations/messages/{message.id}/attachment/?inline")
        self.assertIn("inline", inline.headers["Content-Disposition"])

        detail = self.client.get(f"/api/v1/conversations/{message.conversation_id}/").json()
        payload = next(m for m in detail["conversation"]["messages"] if m["id"] == message.id)
        self.assertEqual(payload["kind"], "file")
        self.assertEqual(payload["attachmentName"], "смета.pdf")
        self.assertEqual(payload["attachmentSize"], 4)
        self.assertTrue(payload["attachmentUrl"].endswith(f"/messages/{message.id}/attachment/"))

        outsider = HumanUser.objects.create_user(email="stranger@example.com", password="Password-123")
        other = Organization.objects.create(name="Other", slug="file-other")
        OrganizationMembership.objects.create(user=outsider, organization=other, role=EmployeeRole.OWNER, position_title="Owner")
        foreign = APIClient()
        foreign.force_authenticate(outsider)
        self.assertEqual(foreign.get(f"/api/v1/conversations/messages/{message.id}/attachment/").status_code, 404)

    def test_operator_sends_file_and_claims_dialog(self) -> None:
        conversation = self._conversation()
        self.assertNotEqual(conversation.control_mode, ControlMode.HUMAN)

        with mock.patch("chatballs.conversations.transports.send_file", return_value=True) as send:
            response = self.client.post(
                f"/api/v1/conversations/{conversation.id}/attachments/",
                data={"file": SimpleUploadedFile("прайс.pdf", b"%PDF-1", content_type="application/pdf"), "text": "Прайс"},
                format="multipart",
            )
        self.assertEqual(response.status_code, 201, response.content)
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs["filename"], "прайс.pdf")
        self.assertEqual(kwargs["caption"], "Прайс")
        self.assertEqual(kwargs["chat_id"], "c-1")
        self.assertEqual(kwargs["user_id"], "u-1")

        conversation.refresh_from_db()
        self.assertEqual(conversation.control_mode, ControlMode.HUMAN)
        self.assertEqual(conversation.assigned_operator_id, self.owner.id)
        sent = conversation.messages.get(author_type=MessageAuthor.OPERATOR)
        self.assertEqual(sent.kind, MessageKind.FILE)
        self.assertEqual(sent.text, "Прайс")
        self.assertEqual(sent.attachment_size, 6)
        self.assertTrue(sent.attachment)
        payload = response.json()["message"]
        self.assertEqual(payload["attachmentName"], "прайс.pdf")

    def test_blocked_and_oversized_files_are_rejected(self) -> None:
        conversation = self._conversation()
        with mock.patch("chatballs.conversations.transports.send_file", return_value=True) as send:
            blocked = self.client.post(
                f"/api/v1/conversations/{conversation.id}/attachments/",
                data={"file": SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")},
                format="multipart",
            )
            self.assertEqual(blocked.status_code, 400)
            with mock.patch("chatballs.conversations.attachment_views.MAX_FILE_BYTES", 3):
                big = self.client.post(
                    f"/api/v1/conversations/{conversation.id}/attachments/",
                    data={"file": SimpleUploadedFile("a.txt", b"1234", content_type="text/plain")},
                    format="multipart",
                )
            self.assertEqual(big.status_code, 400)
        send.assert_not_called()
        self.assertEqual(conversation.messages.count(), 0)

    def test_transport_failure_does_not_store_message(self) -> None:
        conversation = self._conversation()
        with mock.patch("chatballs.conversations.transports.send_file", return_value=False):
            response = self.client.post(
                f"/api/v1/conversations/{conversation.id}/attachments/",
                data={"file": SimpleUploadedFile("a.txt", b"1234", content_type="text/plain")},
                format="multipart",
            )
        self.assertEqual(response.status_code, 502)
        self.assertFalse(conversation.messages.exclude(author_type=MessageAuthor.SYSTEM).exists())

    def test_telegram_send_file_picks_photo_or_document(self) -> None:
        from chatballs.conversations.transports import telegram

        urls: list[str] = []

        def fake_multipart(url, **kwargs):
            urls.append(url)
            return {"ok": True}

        with mock.patch("chatballs.conversations.transports.telegram.request_json_multipart", fake_multipart):
            self.assertTrue(telegram.send_file(self.integration, chat_id="c-1", user_id="", content=b"J", filename="p.jpg", content_type="image/jpeg", caption="!"))
            self.assertTrue(telegram.send_file(self.integration, chat_id="c-1", user_id="", content=b"%PDF", filename="d.pdf", content_type="application/pdf"))
        self.assertTrue(urls[0].endswith("/sendPhoto"))
        self.assertTrue(urls[1].endswith("/sendDocument"))

    def test_max_send_file_uploads_then_sends_attachment(self) -> None:
        from chatballs.conversations.transports import max as max_transport

        integration = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.MAX,
            name="MAX",
            secret="max-token",
            channel=self.channel,
        )
        posted: list[dict] = []

        def fake_request_json(url, **kwargs):
            if "/uploads?type=file" in url:
                return {"url": "https://upload.example/put"}
            posted.append(kwargs.get("body") or {})
            return {"message": {"body": {"mid": "m-1"}}}

        with mock.patch("chatballs.conversations.transports.max.request_json", fake_request_json), mock.patch(
            "chatballs.conversations.transports.max.request_json_multipart", return_value={"token": "attach-1"}
        ):
            self.assertTrue(max_transport.send_file(integration, chat_id="", user_id="u-9", content=b"%PDF", filename="d.pdf", content_type="application/pdf", caption="Смета"))
        self.assertEqual(posted[0]["attachments"], [{"type": "file", "payload": {"token": "attach-1"}}])
        self.assertEqual(posted[0]["text"], "Смета")

    def test_email_send_file_adds_mime_attachment(self) -> None:
        from chatballs.conversations.transports import email as email_transport

        integration = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.EMAIL,
            name="Почта",
            secret="pass",
            channel=self.channel,
            config={"email": "support@example.com", "smtp_host": "smtp.example.com", "smtp_ssl": True},
        )
        sent: list = []

        class FakeSMTP:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def login(self, *args):
                pass

            def send_message(self, message):
                sent.append(message)

        with mock.patch("chatballs.conversations.transports.email.smtplib.SMTP_SSL", FakeSMTP):
            self.assertTrue(email_transport.send_file(integration, chat_id="client@example.com", user_id="", content=b"%PDF", filename="смета.pdf", content_type="application/pdf"))
        attachments = list(sent[0].iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_filename(), "смета.pdf")
        self.assertEqual(attachments[0].get_content(), b"%PDF")
