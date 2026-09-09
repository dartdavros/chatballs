from unittest import mock

from django.test import TestCase

from chatballs.conversations.transports.base import InboundMessage
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import HumanUser, Organization
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.notifications.binding import deep_link, handle_notifier_inbound, issue_binding_code
from chatballs.notifications.delivery import NOTIFICATION_CREATED
from chatballs.notifications.models import (
    MessengerBinding,
    MessengerBindingCode,
    NotificationAudience,
    NotificationType,
)
from chatballs.notifications.selectors import visible_for
from chatballs.notifications.services import notify
from chatballs.testing import TenantAPIClient as APIClient
from chatballs.testing import tenant_context_for


def _notifier(organization, provider=IntegrationProvider.TELEGRAM, username="chatballs_notify_bot"):
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
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.owner = HumanUser.objects.get(email="owner@example.com")
        self.context = tenant_context_for(self.owner, self.organization)
        self.integration = _notifier(self.organization)


class BindingTests(NotifierTestBase):
    def test_deep_link_for_telegram_and_max(self) -> None:
        code = issue_binding_code(context=self.context, integration=self.integration)
        self.assertEqual(deep_link(self.integration, code.code), f"https://t.me/chatballs_notify_bot?start={code.code}")
        max_bot = _notifier(self.organization, provider=IntegrationProvider.MAX, username="chatballs_max_bot")
        self.assertEqual(deep_link(max_bot, "abc"), "https://max.ru/chatballs_max_bot?start=abc")

    def test_start_code_creates_binding_and_confirms(self) -> None:
        code = issue_binding_code(context=self.context, integration=self.integration)
        inbound = InboundMessage(external_id="1", user_id="777", chat_id="777", text=f"/start {code.code}", display_name="Андрей")
        with mock.patch("chatballs.notifications.binding.transports.send_reply", return_value=True) as send:
            handle_notifier_inbound(self.integration, inbound)
        binding = MessengerBinding.objects.get(user=self.owner, integration=self.integration)
        self.assertEqual(binding.external_chat_id, "777")
        self.assertFalse(MessengerBindingCode.objects.filter(user=self.owner).exists())
        self.assertIn("подключены", send.call_args.kwargs["text"])

    def test_unknown_text_gets_hint_without_binding(self) -> None:
        inbound = InboundMessage(external_id="2", user_id="777", chat_id="777", text="Привет", display_name="Андрей")
        with mock.patch("chatballs.notifications.binding.transports.send_reply", return_value=True) as send:
            handle_notifier_inbound(self.integration, inbound)
        self.assertFalse(MessengerBinding.objects.exists())
        self.assertIn("профиль", send.call_args.kwargs["text"])

    def test_binding_is_exclusive_across_messengers(self) -> None:
        # Уведомления идут в один мессенджер: привязка MAX заменяет привязку TG.
        MessengerBinding.objects.create(user=self.owner, integration=self.integration, external_chat_id="111")
        max_bot = _notifier(self.organization, provider=IntegrationProvider.MAX, username="chatballs_max_bot")
        code = issue_binding_code(context=self.context, integration=max_bot)
        inbound = InboundMessage(external_id="3", user_id="9", chat_id="9", text=f"/start {code.code}", display_name="Андрей")
        with mock.patch("chatballs.notifications.binding.transports.send_reply", return_value=True):
            handle_notifier_inbound(max_bot, inbound)
        bindings = list(MessengerBinding.objects.filter(user=self.owner))
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0].integration_id, max_bot.id)

    def test_reissue_invalidates_previous_code(self) -> None:
        first = issue_binding_code(context=self.context, integration=self.integration)
        issue_binding_code(context=self.context, integration=self.integration)
        self.assertFalse(MessengerBindingCode.objects.filter(code=first.code).exists())


class DeliveryTests(NotifierTestBase):
    def setUp(self) -> None:
        super().setUp()
        MessengerBinding.objects.create(user=self.owner, integration=self.integration, external_chat_id="777")

    def _dispatch_last_event(self) -> None:
        event = OutboxEvent.objects.filter(event_type=NOTIFICATION_CREATED).latest("created_at")
        dispatch(event)

    def test_notify_enqueues_and_delivers_to_binding(self) -> None:
        with mock.patch("chatballs.notifications.delivery.transports.send_reply", return_value=True) as send:
            notify(
                context=self.context,
                type=NotificationType.DIALOG_WAITING,
                audience=NotificationAudience.OPERATORS,
                title="Новый диалог · Acme — сайт",
                body="Гость · TELEGRAM: Привет",
            )
            self._dispatch_last_event()
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["chat_id"], "777")
        self.assertIn("Новый диалог", send.call_args.kwargs["text"])

    def test_type_not_in_push_types_is_skipped(self) -> None:
        # INTEGRATION_ERROR не входит в дефолтные push_types привязки.
        with mock.patch("chatballs.notifications.delivery.transports.send_reply", return_value=True) as send:
            notify(
                context=self.context,
                type=NotificationType.INTEGRATION_ERROR,
                audience=NotificationAudience.OWNER,
                title="Ошибка интеграции",
            )
            self._dispatch_last_event()
        send.assert_not_called()

    def test_user_audience_only_reaches_recipient(self) -> None:
        operator = HumanUser.objects.get(email="staff.member@example.org")
        with mock.patch("chatballs.notifications.delivery.transports.send_reply", return_value=True) as send:
            notify(
                context=self.context,
                type=NotificationType.DIALOG_NEW_MESSAGE,
                audience=NotificationAudience.USER,
                recipient_user=operator,
                title="Новое сообщение",
            )
            self._dispatch_last_event()
        send.assert_not_called()  # у оператора нет привязки; owner не адресат

    def test_operator_sees_operator_audience_but_not_owner_audience(self) -> None:
        operator = HumanUser.objects.get(email="staff.member@example.org")
        operators_notification = notify(
            context=self.context,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title="Waiting dialog",
        )
        notify(
            context=self.context,
            type=NotificationType.INTEGRATION_ERROR,
            audience=NotificationAudience.OWNER,
            title="Owner-only notice",
        )
        self.assertEqual(
            list(visible_for(tenant_context_for(operator, self.organization)).values_list("id", flat=True)),
            [operators_notification.id],
        )


class PollerSelectionTests(NotifierTestBase):
    """Клиентские боты (без purpose) поллятся; сервисные — нет.

    Регрессия: JSON-exclude по отсутствующему ключу отбрасывал в SQL и строки
    без ключа purpose — клиентские TG/MAX боты переставали поллиться."""

    def test_client_bot_still_polled_notifier_excluded(self) -> None:
        from chatballs.channels.models import Channel
        from chatballs.conversations import poller

        channel = Channel.objects.create(organization=self.organization, code="app-sales", name="Acme — продажи")
        client_bot = Integration.objects.create(
            organization=self.organization, kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM, name="client-bot", secret="token", channel=channel,
        )
        with mock.patch("chatballs.conversations.poller.transports.poll", return_value=([], "")) as poll:
            poller.poll_all_messengers(self.context)
        polled_ids = [call.args[0].id for call in poll.call_args_list]
        self.assertIn(client_bot.id, polled_ids)
        self.assertNotIn(self.integration.id, polled_ids)

    def test_disabled_connection_and_inactive_channel_are_not_polled(self) -> None:
        from chatballs.channels.models import Channel
        from chatballs.conversations import poller

        active_channel = Channel.objects.create(
            organization=self.organization,
            code="active-channel",
            name="Активный канал",
        )
        inactive_channel = Channel.objects.create(
            organization=self.organization,
            code="inactive-channel",
            name="Неактивный канал",
            is_active=False,
        )
        Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="disabled-client",
            secret="token",
            channel=active_channel,
            is_active=False,
        )
        Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="inactive-channel-client",
            secret="token",
            channel=inactive_channel,
        )

        with mock.patch(
            "chatballs.conversations.poller.transports.poll",
            return_value=([], ""),
        ) as poll:
            poller.poll_all_messengers(self.context)

        polled_names = [call.args[0].name for call in poll.call_args_list]
        self.assertNotIn("disabled-client", polled_names)
        self.assertNotIn("inactive-channel-client", polled_names)


class BindingApiTests(NotifierTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def test_list_issue_and_unbind(self) -> None:
        listed = self.client.get("/api/v1/notifications/messenger-bindings/")
        self.assertEqual(listed.status_code, 200)
        item = listed.json()["items"][0]
        self.assertEqual(item["provider"], "TELEGRAM")
        self.assertFalse(item["bound"])

        issued = self.client.post(f"/api/v1/notifications/messenger-bindings/{self.integration.id}/")
        self.assertEqual(issued.status_code, 201)
        payload = issued.json()
        self.assertTrue(payload["deepLink"].startswith("https://t.me/chatballs_notify_bot?start="))

        MessengerBinding.objects.create(user=self.owner, integration=self.integration, external_chat_id="777")
        self.assertTrue(self.client.get("/api/v1/notifications/messenger-bindings/").json()["items"][0]["bound"])

        removed = self.client.delete(f"/api/v1/notifications/messenger-bindings/{self.integration.id}/")
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(MessengerBinding.objects.exists())

    def test_push_types_patch_and_listing(self) -> None:
        MessengerBinding.objects.create(user=self.owner, integration=self.integration, external_chat_id="777")
        listed = self.client.get("/api/v1/notifications/messenger-bindings/").json()
        self.assertIn({"code": NotificationType.DIALOG_WAITING, "label": "Диалог ждёт оператора"}, listed["availableTypes"])
        self.assertIn(NotificationType.DIALOG_WAITING, listed["items"][0]["pushTypes"])

        patched = self.client.patch(
            f"/api/v1/notifications/messenger-bindings/{self.integration.id}/",
            data={"pushTypes": [NotificationType.INTEGRATION_ERROR, "NOT_A_TYPE"]},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["pushTypes"], [NotificationType.INTEGRATION_ERROR])
