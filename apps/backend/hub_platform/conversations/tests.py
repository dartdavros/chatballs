from unittest import mock

from django.test import TestCase

from hub_platform.ai.limits import LimitExceeded
from hub_platform.ai.models import AIAgent
from hub_platform.channels.models import Channel
from hub_platform.conversations.models import ControlMode, ExpectedResponder, Message, MessageAuthor
from hub_platform.conversations.transports.base import InboundMessage
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Organization
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider


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
        AIAgent.objects.create(channel=self.channel, name="FoxRay Agent", model="openai/gpt-4o-mini")
        self.integration = _messenger_connection(self.channel)
        self.inbound = InboundMessage(
            external_id="ext-1", user_id="user-1", chat_id="chat-1", text="Здравствуйте", display_name="Гость"
        )

    def test_limit_exceeded_hands_off_to_operator(self) -> None:
        from hub_platform.conversations.ingest import ingest_inbound

        with (
            mock.patch(
                "hub_platform.conversations.ingest.run_channel_turn",
                side_effect=LimitExceeded("Channel daily AI cost limit reached"),
            ),
            mock.patch("hub_platform.conversations.ingest.transports.send_reply", return_value=True) as send,
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
