"""Проверочный HTTP-чат: данные в памяти, привязки, маски и след вызова."""

import json
from unittest.mock import patch

from django.db import connection
from django.test import TransactionTestCase

from chatballs.ai.models import AgentTool, AIAgent, AIAgentStatus, LlmInvocation
from chatballs.ai.provider.demo import DemoProvider
from chatballs.ai.tool_loop_testing import ScriptedProvider, calls, says
from chatballs.channels.models import Channel
from chatballs.conversations.models import (
    Contact,
    ContactFieldValue,
    Conversation,
    Message,
)
from chatballs.events.models import OutboxEvent
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from chatballs.integrations.tool_client import ToolResponse
from chatballs.testing import TenantAPIClient


class TestChatTests(TransactionTestCase):
    def setUp(self):
        # Только изолированная тестовая БД; штатный контур не получает seed.
        self.organization = Organization.objects.create(name="Test chat", slug="test-chat")
        self.user = HumanUser.objects.create(email="test-chat-admin@example.test")
        OrganizationMembership.objects.create(
            organization=self.organization, user=self.user, role=EmployeeRole.ADMIN,
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.user)
        self.client.set_tenant(self.organization)
        self.channel = Channel.objects.create(
            organization=self.organization, code="preview", name="Preview",
        )
        self.agent = AIAgent.objects.create(
            organization=self.organization, channel=self.channel, name="Preview",
            status=AIAgentStatus.ACTIVE, history_limit=1,
        )
        self.web = self._web(self.channel)
        self.http = Integration.objects.create(
            organization=self.organization, name="Статус заказа",
            kind=IntegrationKind.EXTERNAL_SERVER, provider=IntegrationProvider.HTTP,
            config={
                "tool_name": "order_status", "description": "Статус заказа",
                "method": "GET", "url": "https://shop.example.test/orders/{order_number}",
                "is_enabled": True,
                "parameters": [{
                    "name": "order_number", "type": "string", "required": True,
                    "location": "path", "source": {
                        "type": "web_field", "integration_id": self.web.id, "key": "order_number",
                    },
                }],
            },
        )
        AgentTool.objects.create(
            organization=self.organization, agent=self.agent,
            integration=self.http, tool_name="",
        )
        self.url = f"/api/v1/agents/{self.channel.id}/test-chat/"
        self.data = {
            "name": "Анна", "email": "anna@example.test", "phone": "+79990001122",
            "webFields": {str(self.web.id): {"order_number": "10482"}},
        }

    def _web(self, channel):
        return Integration.objects.create(
            organization=channel.organization, channel=channel, name=f"Web {channel.id}",
            kind=IntegrationKind.MESSENGER, provider=IntegrationProvider.WEB,
            config={"fields": [
                {"key": "order_number", "label": "Номер заказа", "type": "string", "ai_access": "masked"},
                {"key": "amount", "label": "Сумма", "type": "number"},
                {"key": "active", "label": "Активен", "type": "boolean"},
                {"key": "status", "label": "Статус", "type": "enum", "options": [{"value": "sent", "label": "В пути"}]},
                {"key": "date", "label": "Дата", "type": "datetime"},
                {"key": "other_email", "label": "Почта", "type": "email"},
                {"key": "other_phone", "label": "Телефон", "type": "phone"},
                {"key": "url", "label": "Ссылка", "type": "url"},
            ]},
        )

    def _post(self, data=None, **overrides):
        body = {"message": "Статус заказа?", "clientData": self.data if data is None else data}
        return self.client.post(self.url, {**body, **overrides}, format="json")

    def test_order_number_is_bound_in_http_request_and_values_are_not_saved(self):
        provider = DemoProvider()
        requests = []

        def fetch(url, **kwargs):
            # Ход действительно вышел из tenant_atomic перед сетью.
            self.assertFalse(connection.in_atomic_block)
            requests.append((url, kwargs))
            return ToolResponse(
                status=200, content_type="application/json", url=url,
                body=json.dumps({"status": "В пути", "name": "Анна", "order": "10482"}, ensure_ascii=False).encode(),
            )

        with (
            patch("chatballs.ai.invocation.get_provider", return_value=provider),
            patch.object(provider, "chat", wraps=provider.chat) as chat,
            patch.object(provider, "embed", wraps=provider.embed) as embed,
            patch("chatballs.integrations.http_tool.fetch", side_effect=fetch),
        ):
            with connection.cursor() as cursor:
                cursor.execute("SET ROLE chatballs_runtime_app")
            try:
                response = self._post(message="Анна: статус заказа 10482?")
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("RESET ROLE")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(requests[0][0], "https://shop.example.test/orders/10482")
        self.assertEqual(len(requests), 1)
        self.assertEqual(chat.call_count, 2)
        sent = repr(chat.call_args_list) + repr(embed.call_args_list)
        for value in ("Анна", "anna@example.test", "+79990001122", "10482"):
            self.assertNotIn(value, sent)
        self.assertIn("[[client_name]]", sent)
        self.assertIn("[[order_number]]", sent)
        tool = chat.call_args_list[0].kwargs["tools"][0]
        self.assertNotIn("order_number", tool.parameters["properties"])
        payload = response.json()
        self.assertIn("Анна", payload["reply"])
        self.assertIn("10482", payload["reply"])
        self.assertNotIn("[[", payload["reply"])
        self.assertEqual(len(payload["toolCalls"]), 1)
        trace = payload["toolCalls"][0]
        self.assertEqual((trace["name"], trace["tool"], trace["ok"], trace["errorCode"]), ("order_status", "Статус заказа", True, ""))
        self.assertIsInstance(trace["durationMs"], int)
        self.assertGreaterEqual(trace["durationMs"], 0)
        self.assertEqual(set(trace), {"name", "tool", "ok", "errorCode", "error", "durationMs", "turnId"})
        for model in (Contact, ContactFieldValue, Conversation, Message, OutboxEvent):
            self.assertEqual(model.objects.count(), 0, model.__name__)
        invocations = list(LlmInvocation.objects.values())
        self.assertEqual(len(invocations), 3)  # embedding + оба раунда
        self.assertEqual(payload["promptTokens"], sum(row["prompt_tokens"] for row in invocations if row["operation"] == "chat"))
        for value in ("Анна", "anna@example.test", "+79990001122", "10482", "[["):
            self.assertNotIn(value, repr(invocations))

    def test_invalid_data_is_rejected_before_any_provider_or_storage_call(self):
        invalid = [[], {"unexpected": "value"}, {"name": 2}, {"name": "x" * 256},
                   {"email": "broken"}, {"phone": "broken"}, {"webFields": []},
                   {"webFields": {"999999": {}}}]
        for key, value in (("amount", True), ("active", "yes"), ("status", "unknown"),
                           ("date", "broken"), ("other_email", "broken"), ("other_phone", "broken"),
                           ("url", "broken"), ("order_number", 2), ("deleted", "value")):
            invalid.append({"webFields": {str(self.web.id): {key: value}}})
        with patch("chatballs.ai.invocation.get_provider") as provider:
            for data in invalid:
                with self.subTest(data=data):
                    response = self._post(data)
                    self.assertEqual(response.status_code, 400, response.content)
            provider.assert_not_called()
        self.assertEqual(LlmInvocation.objects.count(), 0)
        self.assertEqual(Contact.objects.count(), 0)

    def test_fields_from_another_agent_or_organization_are_rejected(self):
        other = Channel.objects.create(organization=self.organization, code="other", name="Other")
        foreign_org = Organization.objects.create(name="Foreign", slug="foreign-chat")
        foreign = Channel.objects.create(organization=foreign_org, code="foreign", name="Foreign")
        for web in (self._web(other), self._web(foreign)):
            response = self._post({"webFields": {str(web.id): {"order_number": "10482"}}})
            self.assertEqual(response.status_code, 400)

    def test_empty_data_omits_required_bound_tool_and_keeps_legacy_request(self):
        provider = DemoProvider()
        with (
            patch("chatballs.ai.invocation.get_provider", return_value=provider),
            patch.object(provider, "chat", wraps=provider.chat) as chat,
            patch("chatballs.integrations.http_tool.fetch") as fetch,
        ):
            for body in ({"message": "Привет"}, {"message": "Привет", "clientData": {}}):
                response = self.client.post(self.url, body, format="json")
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()["toolCalls"], [])
                self.assertIsNone(chat.call_args.kwargs.get("tools"))
            fetch.assert_not_called()

    def test_tool_error_is_returned_without_foreign_body(self):
        provider = DemoProvider()
        with (
            patch("chatballs.ai.invocation.get_provider", return_value=provider),
            patch("chatballs.integrations.http_tool.fetch", side_effect=TimeoutError("private-body")),
        ):
            response = self._post()
        self.assertEqual(response.status_code, 200, response.content)
        trace = response.json()["toolCalls"][0]
        self.assertFalse(trace["ok"])
        self.assertEqual(trace["errorCode"], "timeout")
        self.assertTrue(trace["error"])
        self.assertNotIn("private-body", response.content.decode())

    def test_history_window_and_provider_failure_keep_tool_trace(self):
        from chatballs.ai.provider.base import ProviderRejected

        provider = ScriptedProvider(calls(("order_status", {})), ProviderRejected("unavailable"))
        with (
            patch("chatballs.ai.invocation.get_provider", return_value=provider),
            patch("chatballs.integrations.http_tool.fetch", side_effect=TimeoutError),
        ):
            response = self._post(history=[
                {"role": "user", "content": "discarded"},
                {"role": "assistant", "content": "Анна"},
            ])
        self.assertEqual(response.status_code, 502, response.content)
        self.assertEqual(response.json()["toolCalls"][0]["errorCode"], "timeout")
        self.assertNotIn("discarded", provider.sent())
        self.assertNotIn("Анна", provider.sent())

    def test_active_agent_and_management_permission_are_required(self):
        self.agent.status = AIAgentStatus.DISABLED
        self.agent.save(update_fields=["status"])
        self.assertEqual(self._post().status_code, 502)
        OrganizationMembership.objects.filter(user=self.user).update(role=EmployeeRole.EMPLOYEE)
        self.assertEqual(self._post().status_code, 403)

    def test_contact_bindings_and_valid_schema_types(self):
        from urllib.parse import parse_qs, urlsplit

        self.http.config["parameters"] += [{
            "name": key, "type": "string", "required": True, "location": "query",
            "source": {"type": "contact", "field": key},
        } for key in ("name", "email", "phone")]
        self.http.save(update_fields=["config"])
        self.data["webFields"][str(self.web.id)].update({
            "amount": 0, "active": False, "status": "sent", "date": "2026-10-05T12:00:00Z",
            "other_email": "another@example.test", "other_phone": "+79990002233",
            "url": "https://example.test/order",
        })
        with (
            patch("chatballs.ai.invocation.get_provider", return_value=DemoProvider()),
            patch("chatballs.integrations.http_tool.fetch", side_effect=TimeoutError) as fetch,
        ):
            response = self._post()
        self.assertEqual(response.status_code, 200, response.content)
        query = parse_qs(urlsplit(fetch.call_args.args[0]).query)
        self.assertEqual(query, {key: [self.data[key]] for key in ("name", "email", "phone")})

    def test_reset_does_not_reuse_values_from_previous_request(self):
        with (
            patch("chatballs.ai.invocation.get_provider", return_value=DemoProvider()),
            patch("chatballs.integrations.http_tool.fetch", side_effect=TimeoutError) as fetch,
        ):
            self.assertEqual(self._post().status_code, 200)
            fetch.reset_mock()
            response = self._post({})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["toolCalls"], [])
        fetch.assert_not_called()

    def test_escaped_values_are_masked_and_restored_without_escaping_artifacts(self):
        self.data["name"] = 'Анна "Ким"\nТест'
        self.data["webFields"][str(self.web.id)]["order_number"] = 'ЛичныйЗаказ42 "А"\n42'
        provider = ScriptedProvider(says("[[client_name]]: [[order_number]]"))
        with patch("chatballs.ai.invocation.get_provider", return_value=provider):
            response = self._post()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["reply"], 'Анна "Ким"\nТест: ЛичныйЗаказ42 "А"\n42')
        self.assertNotIn("Анна", provider.sent())
        self.assertNotIn("ЛичныйЗаказ42", provider.sent())
