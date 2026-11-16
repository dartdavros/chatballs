"""Ход AI как отдельная работа: приём не ждёт модель, ответ считается событием."""

from unittest import mock

from django.test import TestCase, override_settings

from chatballs.ai.models import AIAgent, AIAgentStatus
from chatballs.channels.models import Channel
from chatballs.conversations.ai_turn import AI_TURN_REQUESTED
from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import (
    AiTurnState,
    ControlMode,
    ExpectedResponder,
    Message,
    MessageAuthor,
)
from chatballs.conversations.transports.base import InboundMessage
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from chatballs.testing import ai_answer, run_pending_ai_turns


class AiTurnQueueTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(mock.patch("chatballs.conversations.transports.download_avatar", return_value=None))
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.channel = Channel.objects.create(
            organization=self.organization, code="line", name="Линия"
        )
        provider = Integration.objects.create(organization=self.organization, kind=IntegrationKind.LLM_PROVIDER,
                                              provider=IntegrationProvider.DEMO, name="Demo", secret="demo")
        AIAgent.objects.create(
            provider_integration=provider,
            channel=self.channel,
            name="Агент",
            model="openai/gpt-4o-mini",
            status=AIAgentStatus.ACTIVE,
        )
        self.integration = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="Bot",
            secret="token",
            channel=self.channel,
        )
        self.inbound = InboundMessage(
            external_id="ext-1",
            user_id="u-1",
            chat_id="c-1",
            text="Здравствуйте",
            display_name="Гость",
        )

    def _inbound_message(self) -> Message:
        return Message.objects.get(author_type=MessageAuthor.CONTACT)

    def _ai_messages(self):
        return Message.objects.filter(author_type=MessageAuthor.AI)

    def test_ingest_queues_the_turn_and_does_not_call_the_model(self) -> None:
        # Главное свойство всей развязки: приём не ждёт провайдера.
        with mock.patch("chatballs.ai.provider.local.LocalProvider.chat") as chat:
            ingest_inbound(self.integration, self.inbound)

        chat.assert_not_called()
        message = self._inbound_message()
        self.assertEqual(message.ai_turn_state, AiTurnState.PENDING)
        self.assertFalse(self._ai_messages().exists())
        self.assertTrue(
            OutboxEvent.objects.filter(
                event_type=AI_TURN_REQUESTED, aggregate_id=str(message.conversation_id)
            ).exists()
        )

    def test_turn_answers_and_closes_the_message(self) -> None:
        with (
            ai_answer("Здравствуйте!"),
            mock.patch(
                "chatballs.conversations.transports.send_reply", return_value=True
            ) as send,
        ):
            ingest_inbound(self.integration, self.inbound)
            self.assertEqual(run_pending_ai_turns(), 1)

        self.assertEqual(self._ai_messages().get().text, "Здравствуйте!")
        self.assertEqual(self._inbound_message().ai_turn_state, AiTurnState.DONE)
        conversation = self.channel.conversations.get()
        self.assertEqual(conversation.control_mode, ControlMode.AI)
        self.assertEqual(conversation.expected_responder, ExpectedResponder.CUSTOMER)
        send.assert_called_once()
        self.assertEqual(conversation.domain_events.filter(event_type="QUEUE_ENTERED", actor_kind="AI").count(), 0)
        self.assertEqual(conversation.domain_events.filter(event_type="PUBLIC_REPLY", actor_kind="AI").count(), 1)

    def test_repeated_delivery_does_not_answer_twice(self) -> None:
        # Событие могут привезти второй раз: процесс упал между ответом и
        # отметкой о нём. Второй ответ клиенту — это хуже, чем ни одного.
        with (
            ai_answer("Здравствуйте!"),
            mock.patch("chatballs.conversations.transports.send_reply", return_value=True),
        ):
            ingest_inbound(self.integration, self.inbound)
            event = OutboxEvent.objects.get(event_type=AI_TURN_REQUESTED)
            dispatch(event)
            dispatch(event)

        self.assertEqual(self._ai_messages().count(), 1)
        conversation = self.channel.conversations.get()
        self.assertEqual(conversation.domain_events.filter(event_type="PUBLIC_REPLY", actor_kind="AI").count(), 1)
        self.assertFalse(conversation.domain_events.filter(event_type="ACCEPTED").exists())

    def test_turn_for_a_dialog_taken_by_an_operator_is_dropped(self) -> None:
        with (
            ai_answer("Здравствуйте!"),
            mock.patch("chatballs.conversations.transports.send_reply", return_value=True),
        ):
            ingest_inbound(self.integration, self.inbound)
            conversation = self.channel.conversations.get()
            conversation.control_mode = ControlMode.HUMAN
            conversation.save(update_fields=["control_mode"])
            run_pending_ai_turns()

        self.assertFalse(self._ai_messages().exists())
        self.assertEqual(self._inbound_message().ai_turn_state, AiTurnState.DONE)

    @override_settings(CHATBALLS_AI_TURN_DEADLINE_SECONDS=0)
    def test_expired_turn_goes_to_the_operator_instead_of_the_model(self) -> None:
        # Ответ, пролежавший в очереди, клиенту уже не нужен — нужен человек.
        with (
            mock.patch("chatballs.ai.provider.local.LocalProvider.chat") as chat,
            mock.patch(
                "chatballs.conversations.transports.send_reply", return_value=True
            ) as send,
        ):
            ingest_inbound(self.integration, self.inbound)
            run_pending_ai_turns()

        chat.assert_not_called()
        conversation = self.channel.conversations.get()
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)
        self.assertEqual(conversation.expected_responder, ExpectedResponder.OPERATOR)
        self.assertEqual(self._inbound_message().ai_turn_state, AiTurnState.FAILED)
        self.assertTrue(self._ai_messages().filter(text__contains="специалисту").exists())
        # Клиент получает этот текст в своём канале, а не только в базе.
        send.assert_called_once()
        self.assertEqual(conversation.domain_events.filter(event_type="QUEUE_ENTERED", actor_kind="AI").count(), 1)
        self.assertEqual(conversation.domain_events.filter(event_type="PUBLIC_REPLY", actor_kind="AI").count(), 1)
