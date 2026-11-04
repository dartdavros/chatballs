"""Основа тестов цикла инструментов: агент с диалогом и провайдер по сценарию."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.utils import timezone

from chatballs.ai.agent_tools_testing import AgentToolsTestCase
from chatballs.ai.models import AIAgent, AIAgentStatus
from chatballs.ai.provider.base import ChatResult, ToolCall
from chatballs.ai.provider.local import LocalProvider
from chatballs.conversations.ai_turn import run_requested_turn
from chatballs.conversations.models import (
    AiTurnState,
    Contact,
    Conversation,
    Message,
    MessageAuthor,
)
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.testing import system_tenant_context

NAME = "Анна"
EMAIL = "anna@example.ru"
PROMPT_TOKENS = 10
COMPLETION_TOKENS = 5


def calls(*requested: tuple[str, dict]) -> ChatResult:
    """Ответ модели, которая вместо текста просит инструменты."""
    return ChatResult(
        text="",
        model="scripted",
        prompt_tokens=PROMPT_TOKENS,
        completion_tokens=COMPLETION_TOKENS,
        tool_calls=tuple(
            ToolCall(id=f"call-{number}", name=name, arguments=arguments)
            for number, (name, arguments) in enumerate(requested)
        ),
    )


def error(code: str) -> str:
    """Результат инструмента, каким модель видит ошибку."""
    return f'{{"error":"{code}"}}'


def says(text: str) -> ChatResult:
    return ChatResult(
        text=text, model="scripted", prompt_tokens=PROMPT_TOKENS, completion_tokens=COMPLETION_TOKENS
    )


class ScriptedProvider(LocalProvider):
    """Отвечает по списку шагов и запоминает всё, что ему прислали.

    Шаг — ответ или исключение; последний шаг повторяется, пока его спрашивают.
    """

    def __init__(self, *steps: ChatResult | Exception) -> None:
        self.steps = list(steps)
        self.requests: list[SimpleNamespace] = []

    def chat(self, *, messages, model, params=None, tools=None):
        self.requests.append(SimpleNamespace(messages=list(messages), params=params, tools=tools))
        step = self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]
        if isinstance(step, Exception):
            raise step
        return step

    def sent(self) -> str:
        """Весь текст, ушедший провайдеру за ход."""
        return "\n".join(
            f"{message.content} {[call.arguments for call in message.tool_calls]}"
            for request in self.requests
            for message in request.messages
        )

    def tool_results(self) -> list[str]:
        """Результаты инструментов, какими их увидела модель в последнем запросе."""
        return [m.content for m in self.requests[-1].messages if m.role == "tool"]


class ToolLoopTestCase(AgentToolsTestCase):
    """Агент «Приёмная» с веб-диалогом клиента; инструменты включает сам тест."""

    def setUp(self) -> None:
        super().setUp()
        self.ai_agent = AIAgent.objects.get(channel__name="Приёмная")
        provider = Integration.objects.create(organization=self.organization, name="Tool loop provider",
            kind=IntegrationKind.LLM_PROVIDER, provider=IntegrationProvider.DEMO, secret="test-provider")
        self.ai_agent.provider_integration = provider
        self.ai_agent.model = "demo"
        self.ai_agent.status = AIAgentStatus.ACTIVE
        self.ai_agent.save(update_fields=["status", "provider_integration", "model"])
        self.channel = self.ai_agent.channel
        self.contact = Contact.objects.create(
            organization=self.organization, name=NAME, email=EMAIL
        )
        connection = Integration.objects.create(
            organization=self.organization, channel=self.channel, name="Web",
            kind=IntegrationKind.MESSENGER, provider=IntegrationProvider.WEB,
        )
        self.conversation = Conversation.objects.create(
            organization=self.organization, channel=self.channel,
            connection=connection, contact=self.contact,
        )

    def _run_turn(
        self, provider: ScriptedProvider, text: str = "Где мой заказ 10482?", *, age: int = 0
    ):
        """Прогнать ход по сообщению клиента; вернуть подмену отправки ответа.

        ``age`` — сколько секунд сообщение уже пролежало в очереди.
        """
        incoming = Message.objects.create(
            organization=self.organization, conversation=self.conversation,
            author_type=MessageAuthor.CONTACT, text=text,
            ai_turn_state=AiTurnState.PENDING,
        )
        if age:
            Message.objects.filter(id=incoming.id).update(
                created_at=timezone.now() - timedelta(seconds=age)
            )
        with (
            patch("chatballs.ai.invocation.get_provider", return_value=provider),
            # The scripted model represents a tool-capable provider. The
            # generic test LocalProvider advertises no tool capability.
            patch("chatballs.ai.turn_tools.cached_tool_support", return_value=True),
            patch("chatballs.conversations.transports.send_reply", return_value=True) as send,
        ):
            run_requested_turn(
                {"messageId": incoming.id, "userId": "visitor"},
                system_tenant_context(self.organization),
            )
        incoming.refresh_from_db()
        self.incoming = incoming
        return send

    def _reply(self) -> str:
        return (
            Message.objects.filter(conversation=self.conversation, author_type=MessageAuthor.AI)
            .order_by("-id")
            .first()
            .text
        )
