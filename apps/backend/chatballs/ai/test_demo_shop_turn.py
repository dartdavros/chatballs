import json

from django.test import SimpleTestCase

from chatballs.ai.provider.base import ChatMessage, ToolSpec
from chatballs.ai.provider.demo import DemoProvider
from chatballs.ai.provider.demo_catalog_turn import PRODUCT, SEARCH
from chatballs.ai.provider.demo_shop_turn import HTTP_STATUS, MCP_ORDER
from chatballs.ai.turn_skills import LOAD_SKILL
from chatballs.ai.turn_templates import PREPARE_REPLY


class NorthWindOrderTurnTests(SimpleTestCase):
    def test_catalog_selection_uses_customer_size_budget_and_live_stock(self):
        tools = [ToolSpec(name, "") for name in (PRODUCT, SEARCH, HTTP_STATUS)]
        messages = [ChatMessage("user", "Нужен костюм XL до 35 000 ₽ для самовывоза")]
        provider = DemoProvider()
        request = provider.chat(messages=messages, model="demo", tools=tools)
        call, = request.tool_calls
        self.assertEqual((call.name, call.arguments), (SEARCH, {"size": "XL", "budget": 35000}))
        messages.extend([
            ChatMessage("assistant", "", tool_calls=request.tool_calls),
            ChatMessage("tool", json.dumps({"products": [
                {"name": "Available model", "basePrice": 24000, "insulation": 100,
                 "membrane": 15000, "availability": [{"available": 1}]},
                {"name": "Sold out model", "basePrice": 27000, "insulation": 120,
                 "membrane": 15000, "availability": [{"available": 0}]},
            ]}), tool_call_id=call.id),
        ])
        response = provider.chat(messages=messages, model="demo", tools=tools)
        self.assertIn("Available model", response.text)
        self.assertNotIn("Sold out model", response.text)

    def test_status_is_rendered_from_mcp_and_http_results(self):
        messages = [
            ChatMessage("system", f'{LOAD_SKILL}\n[{{"id":"skill","name":"Работа с заказами"}}]'),
            ChatMessage("user", "Где заказ № 2042?"),
        ]
        tools = [ToolSpec(name, "") for name in [MCP_ORDER, HTTP_STATUS, LOAD_SKILL, PREPARE_REPLY]]
        provider = DemoProvider()

        def respond(results):
            turn = provider.chat(messages=messages, model="demo", tools=tools)
            self.assertEqual([call.name for call in turn.tool_calls], list(results))
            messages.append(ChatMessage("assistant", "", tool_calls=turn.tool_calls))
            for call in turn.tool_calls:
                messages.append(ChatMessage("tool", json.dumps(results[call.name]), tool_call_id=call.id))
            return turn.tool_calls

        template_id = "9d1da46c-fb86-44ff-8cda-9feaf6f86960"
        respond({LOAD_SKILL: {"templates": [{
            "id": template_id, "schema": {"properties": {"order_no": {}, "status": {}}},
        }]}})
        calls = respond({
            MCP_ORDER: {"number": 2042, "name": "Alpine Pro", "total": 26160},
            HTTP_STATUS: {"number": 2042, "status": "ready"},
        })
        self.assertTrue(all(call.arguments == {"order_number": 2042} for call in calls))
        prepared, = respond({PREPARE_REPLY: {"final_response": "Заказ 2042 готов к выдаче"}})
        self.assertEqual(prepared.arguments, {
            "skill_id": "skill", "template_id": template_id,
            "data": {"order_no": "2042", "status": "Готов к выдаче"},
        })
        final = provider.chat(messages=messages, model="demo", tools=tools)
        self.assertEqual(final.text, "Заказ 2042 готов к выдаче")
