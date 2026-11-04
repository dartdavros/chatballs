"""Событие вызова инструмента: запись в ленту и доставка оператору (SPEC-0023 R-19)."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase
from django.utils.translation import override

from chatballs.ai.tool_calls import ToolCallRecord
from chatballs.ai.tool_loop_testing import EMAIL, ScriptedProvider, ToolLoopTestCase, calls, says
from chatballs.conversations.ai_history import conversation_history
from chatballs.conversations.models import (
    Conversation,
    Message,
    MessageAuthor,
    SystemEvent,
)
from chatballs.conversations.realtime import CONVERSATION_EVENT, conversation_group
from chatballs.conversations.serializers import message_payload
from chatballs.conversations.tool_call_events import record_tool_calls
from chatballs.events.models import OutboxEvent
from chatballs.webchat import test_site_fields as storage_tests
from chatballs.webchat.services import messages_payload

FULL_NAME = "Иванова Анна Сергеевна"
ORDER = {"status": "В пути", "customer": {"full_name": FULL_NAME, "email": EMAIL}}
ORDER_NUMBER = "10482"
MCP_CALL = ("get_order_status", {"order_number": ORDER_NUMBER, "email": "[[client_email]]"})
TITLE = "Статус заказа"


class ToolCallEventTests(ToolLoopTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._enable((self.mcp, "get_order_status"))
        self.server.call_result = {
            "content": [{"type": "text", "text": json.dumps(ORDER, ensure_ascii=False)}]
        }

    def _events(self) -> list[Message]:
        return list(
            Message.objects.filter(
                conversation=self.conversation, system_event=SystemEvent.TOOL_CALLED
            ).order_by("id")
        )

    def test_call_is_written_to_the_feed_before_the_answer(self) -> None:
        self._run_turn(ScriptedProvider(calls(MCP_CALL), says("Заказ в пути.")))

        (event,) = self._events()
        self.assertEqual(event.author_type, MessageAuthor.SYSTEM)
        self.assertEqual(event.text, "")
        duration = event.system_params["durationMs"]
        self.assertIsInstance(duration, int)
        self.assertEqual(
            event.system_params,
            {
                "tool": TITLE,
                "result": "ok",
                "error": "",
                "durationMs": duration,
                "turnId": self.incoming.id,
            },
        )
        answer = Message.objects.get(conversation=self.conversation, author_type=MessageAuthor.AI)
        self.assertLess(event.id, answer.id)

    def test_calls_of_one_turn_share_the_turn_and_keep_their_order(self) -> None:
        self.server.call_result = {"isError": True, "content": [{"type": "text", "text": "boom"}]}
        provider = ScriptedProvider(
            calls(MCP_CALL, ("cancel_order", {"order_number": ORDER_NUMBER})), says("Не удалось.")
        )

        self._run_turn(provider)
        first_turn = self.incoming.id
        self._run_turn(ScriptedProvider(says("Чем ещё помочь?")), text="Спасибо")

        events = self._events()
        self.assertEqual(
            [(e.system_params["tool"], e.system_params["result"], e.system_params["error"]) for e in events],
            [(TITLE, "error", "tool_error"), ("cancel_order", "error", "unknown_tool")],
        )
        # Ход без вызовов событий не оставил.
        self.assertEqual({e.system_params["turnId"] for e in events}, {first_turn})

    def test_failed_turn_still_shows_its_calls(self) -> None:
        # Модель просит инструменты и после лимита раундов: ответа нет, вызовы были.
        self._run_turn(ScriptedProvider(calls(MCP_CALL)))

        events = self._events()
        self.assertEqual(len(events), 5)
        unavailable = Message.objects.get(
            conversation=self.conversation, system_event=SystemEvent.AI_UNAVAILABLE
        )
        self.assertLess(events[-1].id, unavailable.id)

    def test_arguments_and_results_are_not_stored(self) -> None:
        self._run_turn(ScriptedProvider(calls(MCP_CALL), says("Готово.")))

        events = Message.objects.filter(conversation=self.conversation).exclude(
            author_type__in=(MessageAuthor.CONTACT, MessageAuthor.AI)
        )
        stored = repr(list(events.values())) + repr(list(OutboxEvent.objects.values()))
        for value in (ORDER_NUMBER, EMAIL, "client_email", FULL_NAME, "В пути", "order_number"):
            self.assertNotIn(value, stored)

    def test_phrase_is_built_for_the_reader(self) -> None:
        record_tool_calls(
            self._incoming(),
            [
                ToolCallRecord(name="get_order_status", title=TITLE, error="", duration_ms=420),
                ToolCallRecord(name="get_order_status", title=TITLE, error="timeout", duration_ms=30000),
                ToolCallRecord(name="get_order_status", title=TITLE, error="brand_new_code", duration_ms=5),
            ],
        )
        ok, failed, unknown = self._events()

        with override("ru"):
            self.assertEqual(message_payload(ok)["text"], "Агент запросил «Статус заказа» · 0,4 с")
            self.assertEqual(
                message_payload(failed)["text"],
                "Агент запросил «Статус заказа» · ошибка: сервер не ответил",
            )
            self.assertEqual(
                message_payload(unknown)["text"],
                "Агент запросил «Статус заказа» · ошибка: вызов не удался",
            )
        with override("en"):
            self.assertEqual(message_payload(ok)["text"], "The agent called “Статус заказа” · 0.4 s")
            payload = message_payload(failed)
        self.assertEqual(payload["text"], "The agent called “Статус заказа” · error: the server did not respond")
        self.assertEqual(payload["systemEvent"], "tool_called")
        self.assertEqual(
            payload["toolCall"],
            {
                "tool": TITLE,
                "ok": False,
                "errorCode": "timeout",
                "error": "the server did not respond",
                "durationMs": 30000,
                "turnId": failed.system_params["turnId"],
            },
        )

    def test_event_is_announced_over_the_conversation_channel(self) -> None:
        incoming = self._incoming()
        with patch("chatballs.conversations.realtime.publish") as publish, self.captureOnCommitCallbacks(execute=True):
            record_tool_calls(
                incoming, [ToolCallRecord(name="x", title=TITLE, error="", duration_ms=1)]
            )

        publish.assert_any_call(
            conversation_group(self.conversation.id),
            {"type": CONVERSATION_EVENT, "conversationId": self.conversation.id},
        )

    def test_event_does_not_reach_the_model_history(self) -> None:
        self._run_turn(ScriptedProvider(calls(MCP_CALL), says("Заказ в пути.")))

        history = conversation_history(Conversation.objects.get(id=self.conversation.id), 50)
        self.assertEqual([item["role"] for item in history], ["user"])

    def _incoming(self) -> Message:
        return Message.objects.create(
            organization=self.organization, conversation=self.conversation,
            author_type=MessageAuthor.CONTACT, text="Где мой заказ?",
        )


class ToolCallEventWidgetTests(TestCase):
    def setUp(self) -> None:
        storage_tests.SiteFieldApiTests.setUp(self)
        self.token, self.session = storage_tests.SiteFieldApiTests._session(self, {})
        self.conversation = Conversation.objects.create(
            organization=self.organization, channel=self.widget.integration.channel,
            connection=self.widget.integration, contact=self.session.identity.contact,
        )

    def test_event_is_not_sent_to_the_customer_widget(self) -> None:
        incoming = Message.objects.create(
            organization=self.organization, conversation=self.conversation,
            author_type=MessageAuthor.CONTACT, text="Где мой заказ?",
        )
        record_tool_calls(
            incoming, [ToolCallRecord(name="x", title=TITLE, error="", duration_ms=1)]
        )

        self.assertEqual(
            [item["id"] for item in messages_payload(self.session, 0)["messages"]], [incoming.id]
        )
