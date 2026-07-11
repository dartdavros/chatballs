from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from hub_platform.conversations.transports.base import InboundMessage
from hub_platform.events.handlers import dispatch
from hub_platform.events.models import OutboxEvent
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import HumanUser, Organization
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider
from hub_platform.notifications.binding import deep_link, handle_notifier_inbound, issue_binding_code
from hub_platform.notifications.delivery import NOTIFICATION_CREATED
from hub_platform.notifications.models import MessengerBinding, MessengerBindingCode, NotificationAudience, NotificationType
from hub_platform.notifications.services import notify


def _notifier(organization, provider=IntegrationProvider.TELEGRAM, username="edevs_notify_bot"):
    return Integration.objects.create(
        organization=organization,
        kind=IntegrationKind.MESSENGER,
        provider=provider,
        name=f"notify-{provider.lower()}",
        secret="bot-token",
        config={"purpose": "notifications", "bot_username": username},
    )


class NotifierTestBase(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.owner = HumanUser.objects.get(email="owner@edevs.tech")
        self.integration = _notifier(self.organization)


class BindingTests(NotifierTestBase):
    def test_deep_link_for_telegram_and_max(self) -> None:
        code = issue_binding_code(user=self.owner, integration=self.integration)
        self.assertEqual(deep_link(self.integration, code.code), f"https://t.me/edevs_notify_bot?start={code.code}")
        max_bot = _notifier(self.organization, provider=IntegrationProvider.MAX, username="edevs_max_bot")
        self.assertEqual(deep_link(max_bot, "abc"), "https://max.ru/edevs_max_bot?start=abc")

    def test_start_code_creates_binding_and_confirms(self) -> None:
        code = issue_binding_code(user=self.owner, integration=self.integration)
        inbound = InboundMessage(external_id="1", user_id="777", chat_id="777", text=f"/start {code.code}", display_name="Андрей")
        with mock.patch("hub_platform.notifications.binding.transports.send_reply", return_value=True) as send:
            handle_notifier_inbound(self.integration, inbound)
        binding = MessengerBinding.objects.get(user=self.owner, integration=self.integration)
        self.assertEqual(binding.external_chat_id, "777")
        self.assertFalse(MessengerBindingCode.objects.filter(user=self.owner).exists())
        self.assertIn("подключены", send.call_args.kwargs["text"])

    def test_unknown_text_gets_hint_without_binding(self) -> None:
        inbound = InboundMessage(external_id="2", user_id="777", chat_id="777", text="Привет", display_name="Андрей")
        with mock.patch("hub_platform.notifications.binding.transports.send_reply", return_value=True) as send:
            handle_notifier_inbound(self.integration, inbound)
        self.assertFalse(MessengerBinding.objects.exists())
        self.assertIn("профиль", send.call_args.kwargs["text"])

    def test_reissue_invalidates_previous_code(self) -> None:
        first = issue_binding_code(user=self.owner, integration=self.integration)
        issue_binding_code(user=self.owner, integration=self.integration)
        self.assertFalse(MessengerBindingCode.objects.filter(code=first.code).exists())


class DeliveryTests(NotifierTestBase):
    def setUp(self) -> None:
        super().setUp()
        MessengerBinding.objects.create(user=self.owner, integration=self.integration, external_chat_id="777")

    def _dispatch_last_event(self) -> None:
        event = OutboxEvent.objects.filter(event_type=NOTIFICATION_CREATED).latest("created_at")
        dispatch(event.event_type, event.payload)

    def test_notify_enqueues_and_delivers_to_binding(self) -> None:
        with mock.patch("hub_platform.notifications.delivery.transports.send_reply", return_value=True) as send:
            notify(
                organization=self.organization,
                type=NotificationType.DIALOG_WAITING,
                audience=NotificationAudience.OPERATORS,
                title="Новый диалог · Edevs — сайт",
                body="Гость · TELEGRAM: Привет",
            )
            self._dispatch_last_event()
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["chat_id"], "777")
        self.assertIn("Новый диалог", send.call_args.kwargs["text"])

    def test_type_not_in_push_types_is_skipped(self) -> None:
        with mock.patch("hub_platform.notifications.delivery.transports.send_reply", return_value=True) as send:
            notify(
                organization=self.organization,
                type=NotificationType.LIMIT_REACHED,
                audience=NotificationAudience.OWNER,
                title="Достигнут лимит",
            )
            self._dispatch_last_event()
        send.assert_not_called()

    def test_user_audience_only_reaches_recipient(self) -> None:
        operator = HumanUser.objects.get(email="a.kotova@edevs.tech")
        with mock.patch("hub_platform.notifications.delivery.transports.send_reply", return_value=True) as send:
            notify(
                organization=self.organization,
                type=NotificationType.DIALOG_NEW_MESSAGE,
                audience=NotificationAudience.USER,
                recipient_user=operator,
                title="Новое сообщение",
            )
            self._dispatch_last_event()
        send.assert_not_called()  # у оператора нет привязки; owner не адресат


class BindingApiTests(NotifierTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_list_issue_and_unbind(self) -> None:
        listed = self.client.get("/api/v1/notifications/messenger-bindings/")
        self.assertEqual(listed.status_code, 200)
        item = listed.json()["items"][0]
        self.assertEqual(item["provider"], "TELEGRAM")
        self.assertFalse(item["bound"])

        issued = self.client.post(f"/api/v1/notifications/messenger-bindings/{self.integration.id}/")
        self.assertEqual(issued.status_code, 201)
        payload = issued.json()
        self.assertTrue(payload["deepLink"].startswith("https://t.me/edevs_notify_bot?start="))

        MessengerBinding.objects.create(user=self.owner, integration=self.integration, external_chat_id="777")
        self.assertTrue(self.client.get("/api/v1/notifications/messenger-bindings/").json()["items"][0]["bound"])

        removed = self.client.delete(f"/api/v1/notifications/messenger-bindings/{self.integration.id}/")
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(MessengerBinding.objects.exists())
