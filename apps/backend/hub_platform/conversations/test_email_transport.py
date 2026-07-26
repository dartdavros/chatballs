"""Email-транспорт: разбор писем, UID-курсор, тредирование (SPEC-HUB-0025 §5)."""

from email import message_from_bytes, policy
from email.message import EmailMessage as MimeMessage
from unittest import mock

from django.test import TestCase

from hub_platform.channels.models import Channel
from hub_platform.conversations.models import Contact, Conversation, MessageAuthor
from hub_platform.conversations.clients import client_detail, clients_overview
from hub_platform.conversations.serializers import conversation_payload
from hub_platform.conversations.transports import email as email_transport
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider

EMAIL_CONFIG = {
    "email": "support@edevs.tech",
    "imap_host": "imap.test",
    "imap_port": 993,
    "imap_ssl": True,
    "smtp_host": "smtp.test",
    "smtp_port": 465,
    "smtp_ssl": True,
}


def _raw(*, from_="Иван Петров <Ivan@example.com>", subject="Вопрос по FoxRay", text="Здравствуйте!", message_id="<m1@example.com>", html=None, attach=False) -> bytes:
    message = MimeMessage()
    message["From"] = from_
    message["Subject"] = subject
    if message_id:
        message["Message-ID"] = message_id
    if html is not None:
        message.add_alternative(html, subtype="html")
    else:
        message.set_content(text)
    if attach:
        message.add_attachment(b"%PDF", maintype="application", subtype="pdf", filename="doc.pdf")
    return message.as_bytes()


def _parsed(raw: bytes):
    return message_from_bytes(raw, policy=policy.default)


def _integration(**overrides) -> Integration:
    fields = {
        "kind": IntegrationKind.MESSENGER,
        "provider": IntegrationProvider.EMAIL,
        "name": "Почта",
        "secret": "app-password",
        "config": dict(EMAIL_CONFIG),
        "poll_marker": "",
    }
    fields.update(overrides)
    return Integration(**fields)


class EmailNormalizeTests(TestCase):
    def test_plain_message_becomes_inbound_with_thread_meta(self) -> None:
        inbound, message_id = email_transport._normalize(
            _parsed(_raw()), own_address="support@edevs.tech", fallback_id="7:100"
        )
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.external_id, "<m1@example.com>")
        self.assertEqual(inbound.user_id, "ivan@example.com")
        self.assertEqual(inbound.chat_id, "ivan@example.com")
        self.assertEqual(inbound.display_name, "Иван Петров")
        self.assertEqual(inbound.text, "Здравствуйте!")
        self.assertEqual(inbound.thread_meta, {"subject": "Вопрос по FoxRay", "last_message_id": "<m1@example.com>"})
        self.assertEqual(message_id, "<m1@example.com>")

    def test_own_message_is_skipped(self) -> None:
        inbound, _ = email_transport._normalize(
            _parsed(_raw(from_="support@edevs.tech")), own_address="support@edevs.tech", fallback_id="7:100"
        )
        self.assertIsNone(inbound)

    def test_html_only_body_is_flattened_to_text(self) -> None:
        inbound, _ = email_transport._normalize(
            _parsed(_raw(html="<p>Добрый день!</p><p>Сколько стоит &laquo;FoxRay&raquo;?</p>")),
            own_address="support@edevs.tech",
            fallback_id="7:100",
        )
        self.assertIsNotNone(inbound)
        self.assertIn("Добрый день!", inbound.text)
        self.assertIn("«FoxRay»", inbound.text)
        self.assertNotIn("<p>", inbound.text)
        self.assertIn("<p>Добрый день!</p>", inbound.content_html)

    def test_html_body_is_sanitized_before_ingest(self) -> None:
        inbound, _ = email_transport._normalize(
            _parsed(
                _raw(
                    html=(
                        '<p onclick="steal()">Здравствуйте!</p>'
                        '<script>alert("xss")</script>'
                        '<a href="javascript:alert(1)">опасная ссылка</a>'
                        '<a href="https://example.com/path">сайт</a>'
                    )
                )
            ),
            own_address="support@edevs.tech",
            fallback_id="7:100",
        )
        self.assertIsNotNone(inbound)
        self.assertNotIn("onclick", inbound.content_html)
        self.assertNotIn("script", inbound.content_html)
        self.assertNotIn("alert", inbound.content_html)
        self.assertNotIn("javascript:", inbound.content_html)
        self.assertIn('href="https://example.com/path"', inbound.content_html)

    def test_attachments_add_note(self) -> None:
        inbound, _ = email_transport._normalize(
            _parsed(_raw(attach=True)), own_address="support@edevs.tech", fallback_id="7:100"
        )
        self.assertIn("[Вложения не поддерживаются: 1 файл(ов)]", inbound.text)

    def test_missing_message_id_falls_back_to_uid(self) -> None:
        inbound, _ = email_transport._normalize(
            _parsed(_raw(message_id="")), own_address="support@edevs.tech", fallback_id="7:100"
        )
        self.assertEqual(inbound.external_id, "7:100")


class _FakeImap:
    def __init__(self, *, validity: int, next_uid: int, mailbox: dict[int, bytes]):
        self.validity = validity
        self.next_uid = next_uid
        self.mailbox = mailbox

    def select(self, name, readonly=False):
        return "OK", [b""]

    def status(self, name, item):
        value = self.validity if "UIDVALIDITY" in item else self.next_uid
        key = "UIDVALIDITY" if "UIDVALIDITY" in item else "UIDNEXT"
        return "OK", [f"INBOX ({key} {value})".encode()]

    def uid(self, command, *args):
        if command == "SEARCH":
            # Реальный IMAP на «N:*» всегда возвращает и старшее письмо.
            return "OK", [" ".join(str(u) for u in sorted(self.mailbox)).encode() or b""]
        return "OK", [(b"1 (RFC822 {0}", self.mailbox[int(args[0])]), b")"]

    def logout(self):
        return "BYE", []


class EmailPollTests(TestCase):
    def _poll(self, integration, fake):
        with mock.patch.object(email_transport, "_imap_connect", return_value=fake):
            return email_transport.poll_updates(integration)

    def test_first_run_sets_cursor_without_ingesting_history(self) -> None:
        fake = _FakeImap(validity=7, next_uid=100, mailbox={98: _raw(), 99: _raw()})
        messages, marker = self._poll(_integration(poll_marker=""), fake)
        self.assertEqual(messages, [])
        self.assertEqual(marker, "7:99")

    def test_new_mail_after_cursor_is_ingested(self) -> None:
        fake = _FakeImap(validity=7, next_uid=101, mailbox={99: _raw(message_id="<old@example.com>"), 100: _raw()})
        messages, marker = self._poll(_integration(poll_marker="7:99"), fake)
        self.assertEqual([m.external_id for m in messages], ["<m1@example.com>"])
        self.assertEqual(marker, "7:100")

    def test_uidvalidity_change_resets_cursor(self) -> None:
        fake = _FakeImap(validity=8, next_uid=50, mailbox={49: _raw()})
        messages, marker = self._poll(_integration(poll_marker="7:99"), fake)
        self.assertEqual(messages, [])
        self.assertEqual(marker, "8:49")

    def test_connection_error_keeps_cursor(self) -> None:
        integration = _integration(poll_marker="7:99")
        with mock.patch.object(email_transport, "_imap_connect", side_effect=OSError("refused")):
            messages, marker = email_transport.poll_updates(integration)
        self.assertEqual(messages, [])
        self.assertEqual(marker, "7:99")


class EmailSendTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="edevs", name="Edevs — главный сайт")
        self.integration = _integration(organization=self.organization, channel=self.channel)
        self.integration.save()
        contact = Contact.objects.create(organization=self.organization, name="Иван")
        self.conversation = Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.integration,
            contact=contact,
            external_chat_id="ivan@example.com",
            transport_meta={"subject": "Вопрос по FoxRay", "last_message_id": "<m1@example.com>"},
        )

    def test_reply_goes_into_the_same_thread(self) -> None:
        with mock.patch.object(email_transport.smtplib, "SMTP_SSL") as smtp_cls:
            ok = email_transport.send_text(self.integration, chat_id="ivan@example.com", user_id="", text="Добрый день!")
        self.assertTrue(ok)
        smtp = smtp_cls.return_value
        smtp.login.assert_called_once_with("support@edevs.tech", "app-password")
        outgoing = smtp.send_message.call_args.args[0]
        self.assertEqual(outgoing["To"], "ivan@example.com")
        self.assertEqual(outgoing["Subject"], "Re: Вопрос по FoxRay")
        self.assertEqual(outgoing["In-Reply-To"], "<m1@example.com>")
        self.assertEqual(outgoing["References"], "<m1@example.com>")

    def test_send_without_thread_meta_uses_fallback_subject(self) -> None:
        self.conversation.transport_meta = {}
        self.conversation.save(update_fields=["transport_meta"])
        with mock.patch.object(email_transport.smtplib, "SMTP_SSL") as smtp_cls:
            ok = email_transport.send_text(self.integration, chat_id="ivan@example.com", user_id="", text="Добрый день!")
        self.assertTrue(ok)
        outgoing = smtp_cls.return_value.send_message.call_args.args[0]
        self.assertEqual(outgoing["Subject"], "Re: Ваше обращение")
        self.assertIsNone(outgoing["In-Reply-To"])

    def test_smtp_failure_returns_false(self) -> None:
        with mock.patch.object(email_transport.smtplib, "SMTP_SSL", side_effect=OSError("refused")):
            ok = email_transport.send_text(self.integration, chat_id="ivan@example.com", user_id="", text="Привет")
        self.assertFalse(ok)


class EmailIngestThreadMetaTests(TestCase):
    """ingest пишет transport_meta: тема — от первого письма, Message-ID — последний."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="edevs", name="Edevs — главный сайт")
        self.integration = _integration(organization=self.organization, channel=self.channel)
        self.integration.save()

    def _ingest(self, *, external_id: str, subject: str, message_id: str) -> None:
        from hub_platform.conversations.ingest import ingest_inbound
        from hub_platform.conversations.transports.base import InboundMessage

        inbound = InboundMessage(
            external_id=external_id,
            user_id="ivan@example.com",
            chat_id="ivan@example.com",
            text="Здравствуйте!",
            display_name="Иван",
            thread_meta={"subject": subject, "last_message_id": message_id},
        )
        with (
            mock.patch("hub_platform.conversations.ingest.run_channel_turn", return_value=mock.Mock(text="Ответ")),
            mock.patch("hub_platform.conversations.ingest.transports.send_reply", return_value=True),
            mock.patch("hub_platform.conversations.ingest.record_usage"),
        ):
            ingest_inbound(self.integration, inbound)

    def test_subject_pinned_to_first_message_id_follows_last(self) -> None:
        self._ingest(external_id="<m1@example.com>", subject="Вопрос по FoxRay", message_id="<m1@example.com>")
        self._ingest(external_id="<m2@example.com>", subject="Re: Вопрос по FoxRay", message_id="<m2@example.com>")
        conversation = Conversation.objects.get(channel=self.channel)
        self.assertEqual(conversation.transport_meta["subject"], "Вопрос по FoxRay")
        self.assertEqual(conversation.transport_meta["last_message_id"], "<m2@example.com>")
        authors = list(conversation.messages.values_list("author_type", flat=True))
        self.assertIn(MessageAuthor.CONTACT, authors)

    def test_email_identity_is_exposed_in_dialog_and_contact_payloads(self) -> None:
        self._ingest(
            external_id="<identity@example.com>",
            subject="Контакты",
            message_id="<identity@example.com>",
        )
        conversation = Conversation.objects.get(channel=self.channel)
        dialog = conversation_payload(conversation, with_messages=True)
        self.assertEqual(dialog["connection"]["provider"], "EMAIL")
        self.assertEqual(dialog["contact"]["email"], "ivan@example.com")
        self.assertEqual(dialog["messages"][0]["contentHtml"], "")

        overview = clients_overview(self.organization.id)
        self.assertEqual(overview[0]["email"], "ivan@example.com")
        self.assertIn("EMAIL", overview[0]["channels"])

        detail = client_detail(self.organization.id, conversation.contact_id)
        self.assertEqual(detail["email"], "ivan@example.com")
        self.assertEqual(detail["identities"][0]["value"], "ivan@example.com")
