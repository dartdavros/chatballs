"""Псевдонимизация в ходе агента: провайдер видит токены, клиент — значения."""

from unittest.mock import patch

from django.test import TestCase

from chatballs.ai.models import AIAgent, AIAgentStatus, LlmInvocation
from chatballs.ai.provider.base import ChatResult
from chatballs.ai.provider.local import LocalProvider
from chatballs.ai.retrieval import KnowledgeRetriever
from chatballs.ai.runtime import run_agent_turn
from chatballs.channels.models import Channel
from chatballs.conversations.ai_turn import run_requested_turn
from chatballs.conversations.models import (
    AiTurnState,
    Contact,
    Conversation,
    Message,
    MessageAuthor,
)
from chatballs.events.models import OutboxEvent
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.testing import system_tenant_context

NAME = "Анна"
EMAIL = "anna@example.ru"
PHONE = "+7 916 245-14-02"


class _RecordingProvider(LocalProvider):
    """Тестовый провайдер, который запоминает всё, что ему прислали."""

    def __init__(self, reply: str | None = None) -> None:
        self.reply = reply
        self.chat_messages = []
        self.embedded = []

    def chat(self, *, messages, model, params=None):
        self.chat_messages = list(messages)
        if self.reply is None:
            return super().chat(messages=messages, model=model, params=params)
        return ChatResult(text=self.reply, model=model, prompt_tokens=1, completion_tokens=1)

    def embed(self, *, texts, model):
        self.embedded.extend(texts)
        return super().embed(texts=texts, model=model)

    def sent(self) -> str:
        return "\n".join([*(item.content for item in self.chat_messages), *self.embedded])


class TurnPseudonymizationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Masking", slug="masking")
        self.channel = Channel.objects.create(
            organization=self.organization, code="site", name="Site"
        )
        provider = Integration.objects.create(
            organization=self.organization, name="Builtin test provider",
            kind=IntegrationKind.LLM_PROVIDER, provider=IntegrationProvider.DEMO, secret="demo",
        )
        self.agent = AIAgent.objects.create(
            organization=self.organization, channel=self.channel, name="Agent",
            status=AIAgentStatus.ACTIVE, persona="Ассистент.", instructions="Помогай клиенту.",
            provider_integration=provider,
        )
        self.connection = Integration.objects.create(
            organization=self.organization, channel=self.channel, name="Web",
            kind=IntegrationKind.MESSENGER, provider=IntegrationProvider.WEB,
        )
        self.contact = Contact.objects.create(
            organization=self.organization, name=NAME, email=EMAIL, phone=PHONE
        )
        self.conversation = Conversation.objects.create(
            organization=self.organization, channel=self.channel,
            connection=self.connection, contact=self.contact,
        )

    def _message(self, text, **overrides):
        return Message.objects.create(**{
            "organization": self.organization, "conversation": self.conversation,
            "author_type": MessageAuthor.CONTACT, "text": text, **overrides,
        })

    def _run_turn(self, provider, text):
        message = self._message(text, ai_turn_state=AiTurnState.PENDING)
        with (
            patch("chatballs.ai.invocation.get_provider", return_value=provider),
            patch("chatballs.conversations.transports.send_reply", return_value=True) as send,
        ):
            run_requested_turn(
                {"messageId": message.id, "userId": "visitor"},
                system_tenant_context(self.organization),
            )
        message.refresh_from_db()
        self.assertEqual(message.ai_turn_state, AiTurnState.DONE)
        return send

    def _reply(self):
        return Message.objects.get(conversation=self.conversation, author_type=MessageAuthor.AI)

    def test_contact_values_stay_out_of_provider_and_return_in_the_reply(self):
        self._message(f"Здравствуйте, это {NAME}")
        provider = _RecordingProvider(
            "[[client_name]], перезвоним на [[client_phone]], письмо придёт на [[client_email]]."
        )
        send = self._run_turn(
            provider, "Меня зовут анна, телефон 7 (916) 245 14 02, почта ANNA@example.ru"
        )

        question = "Меня зовут [[client_name]], телефон [[client_phone]], почта [[client_email]]"
        self.assertEqual(provider.embedded, [question])
        self.assertEqual(
            [item.content for item in provider.chat_messages[-2:]],
            ["Здравствуйте, это [[client_name]]", question],
        )
        sent = provider.sent().casefold()
        for value in (NAME, EMAIL, "916", "245"):
            self.assertNotIn(value.casefold(), sent)

        expected = f"{NAME}, перезвоним на {PHONE}, письмо придёт на {EMAIL}."
        self.assertEqual(self._reply().text, expected)
        self.assertEqual(send.call_args.kwargs["text"], expected)
        # Исходный текст клиента в базе не меняется.
        self.assertTrue(
            Message.objects.filter(conversation=self.conversation, text__contains="анна").exists()
        )

    def test_token_map_is_not_stored_in_invocations_or_events(self):
        provider = _RecordingProvider("[[client_name]], ждите звонка на [[client_phone]].")
        self._run_turn(provider, f"Это {NAME}, мой номер {PHONE}")

        self.assertEqual(LlmInvocation.objects.filter(channel=self.channel).count(), 2)
        stored = repr(list(LlmInvocation.objects.values())) + repr(list(OutboxEvent.objects.values()))
        for value in (NAME, EMAIL, PHONE, "client_name", "client_phone", "[["):
            self.assertNotIn(value, stored)

    def test_unknown_and_mangled_tokens_are_removed_with_a_warning_without_values(self):
        provider = _RecordingProvider(
            "[[client_nam]], заказ [[order_7]] готов. Спасибо, [[client_name]]!"
        )
        with self.assertLogs("chatballs", level="DEBUG") as logs:
            self._run_turn(provider, f"Это {NAME}, {EMAIL}, где заказ?")

        self.assertEqual(self._reply().text, f", заказ  готов. Спасибо, {NAME}!")
        warnings = [
            record for record in logs.records if record.name == "chatballs.ai.invocation"
        ]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].levelname, "WARNING")
        self.assertEqual(warnings[0].args[0], 2)
        journal = "\n".join(logs.output)
        for value in (NAME, EMAIL, PHONE, "client_nam", "order_7", "[["):
            self.assertNotIn(value, journal)

    def test_retriever_sends_the_masked_question_to_embeddings(self):
        provider = _RecordingProvider()
        with patch("chatballs.ai.invocation.get_provider", return_value=provider):
            KnowledgeRetriever().retrieve(agent=self.agent, query="Почта user@example.test")
        self.assertEqual(provider.embedded, ["Почта [[email_1]]"])

    def test_single_step_turn_masks_the_question_and_restores_the_reply(self):
        # Тестовый провайдер отвечает эхом вопроса: токены возвращаются значениями.
        provider = _RecordingProvider()
        question = "Пишите на user@example.test или звоните +7 800 555-35-35"
        with patch("chatballs.ai.invocation.get_provider", return_value=provider):
            result = run_agent_turn(agent=self.agent, message=question)

        masked = "Пишите на [[email_1]] или звоните [[phone_1]]"
        self.assertEqual(provider.embedded, [masked])
        self.assertEqual(provider.chat_messages[-1].content, masked)
        self.assertTrue(result.result.text.endswith(question))
