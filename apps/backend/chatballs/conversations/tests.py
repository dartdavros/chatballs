import json

from unittest import mock

from django.test import TestCase, override_settings
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.ai.limits import LimitExceeded
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.models import AIAgent, AIAgentStatus
from chatballs.channels.models import Channel
from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    ControlMode,
    Conversation,
    ExpectedResponder,
    Message,
    MessageAuthor,
    MessageKind,
)
from chatballs.conversations.transports.base import InboundMessage
from chatballs.conversations.transports import max as max_transport
from chatballs.conversations.transports import telegram as telegram_transport
from chatballs.identity.bootstrap import bootstrap_edevs_owner
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.notifications.models import Notification, NotificationAudience, NotificationType


def _messenger_connection(channel):
    return Integration.objects.create(
        organization=channel.organization,
        kind=IntegrationKind.MESSENGER,
        provider=IntegrationProvider.TELEGRAM,
        name="test-bot",
        channel=channel,
    )


class IngestLimitHandlingTests(TestCase):
    """При срабатывании дневного лимита стоимости (LimitExceeded) диалог не должен
    «зависать»: его передают оператору с fallback-ответом клиенту (как при сбое
    провайдера). См. ingest.ingest_inbound.
    """

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="foxray-sales", name="FoxRay — продажи")
        AIAgent.objects.create(
            channel=self.channel,
            name="FoxRay Agent",
            model="openai/gpt-4o-mini",
            status=AIAgentStatus.ACTIVE,
        )
        self.integration = _messenger_connection(self.channel)
        self.inbound = InboundMessage(
            external_id="ext-1", user_id="user-1", chat_id="chat-1", text="Здравствуйте", display_name="Гость"
        )

    def test_limit_exceeded_hands_off_to_operator(self) -> None:
        from chatballs.conversations.ingest import ingest_inbound

        with (
            mock.patch(
                "chatballs.conversations.ingest.run_channel_turn",
                side_effect=LimitExceeded("Channel daily AI cost limit reached"),
            ),
            mock.patch("chatballs.conversations.ingest.transports.send_reply", return_value=True) as send,
        ):
            ingest_inbound(self.integration, self.inbound)

        conversation = self.channel.conversations.get()
        # Диалог передан оператору, ответчик — оператор.
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)
        self.assertEqual(conversation.expected_responder, ExpectedResponder.OPERATOR)

        # Сохранены: входящее сообщение, системная отметка и fallback ИИ.
        authors = list(self.channel.conversations.get().messages.values_list("author_type", flat=True))
        self.assertIn(MessageAuthor.CONTACT, authors)
        self.assertIn(MessageAuthor.SYSTEM, authors)
        self.assertIn(MessageAuthor.AI, authors)

        # Fallback отправлен в канал.
        send.assert_called_once()
        self.assertIn("специалисту", send.call_args.kwargs["text"])


class TransportNormalizeTests(TestCase):
    """Разбор входящих: username отправителя и явный шаринг контакта."""

    def test_telegram_text_message_carries_username(self) -> None:
        update = {
            "update_id": 10,
            "message": {
                "text": "Привет",
                "from": {"id": 5, "first_name": "Иван", "last_name": "Петров", "username": "ivan_petrov"},
                "chat": {"id": 7},
            },
        }
        inbound = telegram_transport._normalize(update)
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.username, "ivan_petrov")
        self.assertEqual(inbound.display_name, "Иван Петров")
        self.assertEqual(inbound.phone, "")

    def test_telegram_contact_message_without_text(self) -> None:
        update = {
            "update_id": 11,
            "message": {
                "contact": {"phone_number": "+79991234567", "user_id": 5},
                "from": {"id": 5, "first_name": "Иван", "username": "ivan_petrov"},
                "chat": {"id": 7},
            },
        }
        inbound = telegram_transport._normalize(update)
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.phone, "+79991234567")
        self.assertEqual(inbound.text, "")

    def test_max_contact_attachment_with_vcf(self) -> None:
        update = {
            "update_type": "message_created",
            "message": {
                "sender": {"user_id": 42, "name": "Мария", "username": "maria"},
                "recipient": {"chat_id": 100},
                "body": {
                    "mid": "m-1",
                    "attachments": [
                        {"type": "contact", "payload": {"vcf_info": "BEGIN:VCARD\nTEL;TYPE=CELL:+7 999 111-22-33\nEND:VCARD"}}
                    ],
                },
            },
        }
        inbound = max_transport._normalize(update)
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.phone, "+7 999 111-22-33")
        self.assertEqual(inbound.username, "maria")

    def test_max_bot_started_becomes_start_command_with_payload(self) -> None:
        update = {
            "update_type": "bot_started",
            "timestamp": 1573226679188,
            "chat_id": 555,
            "user": {"user_id": 42, "name": "Иван", "username": "ivan"},
            "payload": "bind-code-123",
        }
        inbound = max_transport._normalize(update)
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.text, "/start bind-code-123")
        self.assertEqual(inbound.chat_id, "555")
        self.assertEqual(inbound.user_id, "42")

    def test_max_text_message_without_contact(self) -> None:
        update = {
            "update_type": "message_created",
            "message": {
                "sender": {"user_id": 42, "name": "Мария"},
                "recipient": {"chat_id": 100},
                "body": {"mid": "m-2", "text": "Здравствуйте"},
            },
        }
        inbound = max_transport._normalize(update)
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.phone, "")
        self.assertEqual(inbound.text, "Здравствуйте")


class ContactShareIngestTests(TestCase):
    """Шаринг контакта: телефон сохраняется в Contact, AI-ход не запускается,
    клиенту уходит подтверждение (в TG — со снятием клавиатуры)."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="foxray-sales", name="FoxRay — продажи")
        AIAgent.objects.create(
            channel=self.channel,
            name="FoxRay Agent",
            model="openai/gpt-4o-mini",
            status=AIAgentStatus.ACTIVE,
        )
        self.integration = _messenger_connection(self.channel)

    def test_username_saved_on_identity(self) -> None:
        from chatballs.conversations.ingest import ingest_inbound

        inbound = InboundMessage(
            external_id="ext-1", user_id="u1", chat_id="c1", text="Привет", display_name="Иван", username="ivan"
        )
        with (
            mock.patch("chatballs.conversations.ingest.run_channel_turn", return_value=mock.Mock(text="Здравствуйте!")),
            mock.patch("chatballs.conversations.ingest.transports.send_reply", return_value=True),
        ):
            ingest_inbound(self.integration, inbound)

        identity = ConnectionIdentity.objects.get(connection=self.integration, external_user_id="u1")
        self.assertEqual(identity.username, "ivan")

    def test_contact_share_saves_phone_without_ai_turn(self) -> None:
        from chatballs.conversations.ingest import ingest_inbound

        inbound = InboundMessage(
            external_id="ext-2", user_id="u1", chat_id="c1", text="", display_name="Иван", username="ivan", phone="+79991234567"
        )
        with (
            mock.patch("chatballs.conversations.ingest.run_channel_turn") as ai_turn,
            mock.patch("chatballs.conversations.ingest.transports.send_contact_ack", return_value=True) as ack,
        ):
            ingest_inbound(self.integration, inbound)

        ai_turn.assert_not_called()
        ack.assert_called_once()
        contact = ConnectionIdentity.objects.get(connection=self.integration, external_user_id="u1").contact
        self.assertEqual(contact.phone, "+79991234567")
        conversation = self.channel.conversations.get()
        kinds = list(conversation.messages.values_list("kind", flat=True))
        self.assertIn(MessageKind.CONTACT, kinds)
        # Подтверждение сохранено в переписке.
        self.assertTrue(conversation.messages.filter(author_type=MessageAuthor.AI, text__icontains="Контакт получен").exists())


class RequestContactApiTests(TestCase):
    """POST /conversations/<id>/request-contact/: сообщение kind=contact_request
    и отправка кнопки в мессенджер; повторный запрос при известном телефоне — 409."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="foxray-sales", name="FoxRay — продажи")
        self.integration = _messenger_connection(self.channel)
        self.contact = Contact.objects.create(organization=self.organization, name="Иван")
        ConnectionIdentity.objects.create(
            contact=self.contact, connection=self.integration, external_user_id="u1", display_name="Иван"
        )
        self.conversation = Conversation.objects.create(
            organization=self.organization, channel=self.channel, connection=self.integration,
            contact=self.contact, external_chat_id="c1",
        )
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_request_contact_creates_message_and_sends_button(self) -> None:
        with mock.patch("chatballs.conversations.services.transports.send_contact_request", return_value=True) as send:
            response = self.client.post(f"/api/v1/conversations/{self.conversation.id}/request-contact/")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"]["kind"], MessageKind.CONTACT_REQUEST)
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["chat_id"], "c1")
        message = self.conversation.messages.get()
        self.assertEqual(message.kind, MessageKind.CONTACT_REQUEST)
        self.assertEqual(message.author_type, MessageAuthor.OPERATOR)

    def test_request_contact_conflict_when_phone_known(self) -> None:
        self.contact.phone = "+79991234567"
        self.contact.save(update_fields=["phone"])
        response = self.client.post(f"/api/v1/conversations/{self.conversation.id}/request-contact/")
        self.assertEqual(response.status_code, 409)

    def test_detail_payload_contains_username_and_phone(self) -> None:
        ConnectionIdentity.objects.filter(contact=self.contact).update(username="ivan")
        self.contact.phone = "+79991234567"
        self.contact.save(update_fields=["phone"])
        response = self.client.get(f"/api/v1/conversations/{self.conversation.id}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["conversation"]["contact"]
        self.assertEqual(payload["username"], "ivan")
        self.assertEqual(payload["phone"], "+79991234567")


class ConversationReadTests(TestCase):
    """Открытие диалога двигает персональную отметку прочтения — бейдж
    непрочитанных (pendingCount) в списке гаснет без ответа оператора."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="foxray-sales", name="FoxRay — продажи")
        self.integration = _messenger_connection(self.channel)
        contact = Contact.objects.create(organization=self.organization, name="Иван")
        self.conversation = Conversation.objects.create(
            organization=self.organization, channel=self.channel, connection=self.integration, contact=contact
        )
        Message.objects.create(conversation=self.conversation, author_type=MessageAuthor.CONTACT, text="Хорошо")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def _pending(self) -> int:
        items = self.client.get("/api/v1/conversations/").json()["items"]
        return next(item["pendingCount"] for item in items if item["id"] == self.conversation.id)

    def test_badge_clears_after_opening_dialog(self) -> None:
        self.assertEqual(self._pending(), 1)
        detail = self.client.get(f"/api/v1/conversations/{self.conversation.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(self._pending(), 0)
        # Новое сообщение клиента снова поднимает бейдж.
        Message.objects.create(conversation=self.conversation, author_type=MessageAuthor.CONTACT, text="Ещё вопрос")
        self.assertEqual(self._pending(), 1)


class ConversationSearchTests(TestCase):
    """Поиск в списке диалогов: имена — подстрокой, тексты сообщений —
    полнотекстово (russian, websearch)."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="line", name="Линия")
        self.integration = _messenger_connection(self.channel)
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def _conversation(self, name: str, text: str) -> Conversation:
        contact = Contact.objects.create(organization=self.organization, name=name)
        conversation = Conversation.objects.create(
            organization=self.organization, channel=self.channel, connection=self.integration, contact=contact
        )
        Message.objects.create(conversation=conversation, author_type=MessageAuthor.CONTACT, text=text)
        return conversation

    def _search(self, query: str) -> list[int]:
        items = self.client.get(f"/api/v1/conversations/?q={query}").json()["items"]
        return [item["id"] for item in items]

    def test_fulltext_matches_message_words_with_morphology(self) -> None:
        order = self._conversation("Мария", "Хочу оформить заказ на костюм")
        self._conversation("Иван", "Когда работает шоурум?")
        # Морфология: «заказы» находит «заказ».
        self.assertEqual(self._search("заказы"), [order.id])

    def test_contact_name_matches_by_substring(self) -> None:
        maria = self._conversation("Мария Соколова", "Добрый день")
        self._conversation("Иван", "Здравствуйте")
        self.assertEqual(self._search("соколов"), [maria.id])


class WebchatContactTests(TestCase):
    """Веб-виджет: клиент отправляет телефон формой — он сохраняется в Contact,
    в переписке появляются kind=contact и подтверждение."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = Channel.objects.create(organization=self.organization, code="edevs-web", name="Веб-чат")
        AIAgent.objects.create(
            channel=self.channel,
            name="Web Agent",
            model="openai/gpt-4o-mini",
            status=AIAgentStatus.ACTIVE,
        )
        from chatballs.webchat.testing import create_web_widget

        self.widget = create_web_widget(self.channel, name="web-widget")
        self.client = APIClient()
        session = self.client.post(
            "/api/v1/webchat/session/",
            data=json.dumps({"widgetKey": self.widget.public_key}),
            content_type="application/json",
        )
        self.token = session.json()["token"]

    def _post_contact(self, phone: str):
        return self.client.post(
            "/api/v1/webchat/contact/",
            data=json.dumps({"phone": phone}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def _post_message(self, text: str):
        return self.client.post(
            "/api/v1/webchat/messages/",
            data=json.dumps({"text": text}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def test_contact_saved_and_ack_visible_in_poll(self) -> None:
        response = self._post_contact("+7 (999) 123-45-67")
        self.assertEqual(response.status_code, 201)
        contact = Contact.objects.exclude(phone="").get()
        self.assertEqual(contact.phone, "+79991234567")

        poll = self.client.get("/api/v1/webchat/messages/?since=0", HTTP_AUTHORIZATION=f"Bearer {self.token}")
        kinds = [m["kind"] for m in poll.json()["messages"]]
        self.assertIn(MessageKind.CONTACT, kinds)

    def test_invalid_phone_rejected(self) -> None:
        response = self._post_contact("12345")
        self.assertEqual(response.status_code, 400)

    @override_settings(CHATBALLS_AI_PROVIDER="")
    def test_missing_provider_integration_hands_off_without_500_and_notifies_management(
        self,
    ) -> None:
        # Агент без BYOK-интеграции: IntegrationNotConfigured (ProviderError)
        # переводит диалог оператору вместо 500 (ADR-HUB-0042 §3).
        admin = HumanUser.objects.create_user(email="admin@edevs.tech", password="temporary")
        OrganizationMembership.objects.create(
            user=admin,
            organization=self.organization,
            role=EmployeeRole.ADMIN,
            position_title="Администратор",
        )

        response = self._post_message("Здравствуйте")

        self.assertEqual(response.status_code, 201)
        conversation = Conversation.objects.get(channel=self.channel)
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)
        self.assertEqual(conversation.expected_responder, ExpectedResponder.OPERATOR)
        self.assertTrue(
            conversation.messages.filter(
                author_type=MessageAuthor.AI,
                text__contains="специалисту",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                type=NotificationType.DIALOG_WAITING,
                audience=NotificationAudience.OPERATORS,
                target_id=str(conversation.id),
            ).exists()
        )
        self.assertEqual(
            set(
                Notification.objects.filter(
                    type=NotificationType.INTEGRATION_ERROR,
                    audience=NotificationAudience.USER,
                    target_id=str(conversation.id),
                ).values_list("recipient_user__email", flat=True)
            ),
            {"owner@edevs.tech", "admin@edevs.tech"},
        )

    def test_provider_error_hands_off_without_500(self) -> None:
        with mock.patch(
            "chatballs.conversations.ingest.run_channel_turn",
            side_effect=ProviderError("AI недоступен"),
        ):
            response = self._post_message("Здравствуйте")

        self.assertEqual(response.status_code, 201)
        conversation = Conversation.objects.get(channel=self.channel)
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)
        self.assertEqual(conversation.expected_responder, ExpectedResponder.OPERATOR)
        self.assertTrue(
            conversation.messages.filter(
                author_type=MessageAuthor.AI,
                text__contains="специалисту",
            ).exists()
        )
