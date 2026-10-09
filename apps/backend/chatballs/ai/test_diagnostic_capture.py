import json
from unittest.mock import patch

from chatballs.ai.diagnostic_models import TurnDiagnostic
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.tool_loop_testing import ScriptedProvider, calls, says
from chatballs.conversations.diagnostic_testing import DiagnosticTestCase
from chatballs.conversations.models import ContactFieldValue, MessageAuthor
from chatballs.conversations.serializers import message_payload
from chatballs.integrations.tool_client import ToolResponse

SITE_SECRET = "real-site-session-secret"


class DiagnosticCaptureTests(DiagnosticTestCase):
    def bind_session(self):
        ContactFieldValue.objects.create(contact=self.conversation.contact, integration=self.web,
                                         key="session_token", value=SITE_SECRET)

    def test_missing_required_token_is_recorded_in_the_actual_turn(self):
        incoming = self.run_turn(ScriptedProvider(says("Нужен специалист.\n<<HANDOFF>>")))
        payload = TurnDiagnostic.objects.get(message=incoming).payload
        self.assertTrue(payload["handoff"])
        self.assertEqual(payload["toolAvailability"][0]["reason"], "required_client_data_unavailable")
        self.assertEqual(payload["toolAvailability"][0]["missingParameters"], ["session_token"])
        self.assertEqual(payload["request"]["tools"], [])
        self.assertIn("<<HANDOFF>>", payload["rounds"][0]["response"]["text"])

    def test_http_calls_and_rounds_are_stored_with_secrets_removed(self):
        self.bind_session()
        result = {"orders": [{"id": "internal-42", "number": "51621"}],
                  "access_token": "upstream-credential"}
        provider = ScriptedProvider(calls(("get_my_orders", {})), says("Заказ найден."))
        with patch("chatballs.integrations.http_tool.fetch", return_value=ToolResponse(
            status=200, content_type="application/json", body=json.dumps(result).encode(), url="",
        )) as fetch:
            incoming = self.run_turn(provider)
        self.assertIn(SITE_SECRET, fetch.call_args.args[0])
        payload = TurnDiagnostic.objects.get(message=incoming).payload
        self.assertEqual(len(payload["rounds"]), 2)
        self.assertEqual(payload["toolAvailability"][0]["reason"], "offered")
        call = payload["toolCalls"][0]
        self.assertEqual(call["diagnostic"]["httpStatus"], 200)
        self.assertIn("internal-42", call["diagnostic"]["modelResult"])
        encoded = json.dumps(payload)
        self.assertNotIn(SITE_SECRET, encoded)
        self.assertNotIn("upstream-credential", encoded)
        self.assertNotIn("toolCalls", json.dumps(message_payload(incoming)))

    def test_http_failure_keeps_status_without_storing_error_body(self):
        self.bind_session()
        with patch("chatballs.integrations.http_tool.fetch", return_value=ToolResponse(
            status=403, content_type="application/json", body=b"private error details", url="",
        )):
            incoming = self.run_turn(ScriptedProvider(calls(("get_my_orders", {})),
                                                    says("Передаю оператору.\n<<HANDOFF>>")))
        payload = TurnDiagnostic.objects.get(message=incoming).payload
        call = payload["toolCalls"][0]
        self.assertEqual(call["error"], "unauthorized")
        self.assertEqual(call["diagnostic"]["httpStatus"], 403)
        self.assertNotIn("private error details", json.dumps(payload))

    def test_order_lookup_then_details_preserves_internal_id_and_round_order(self):
        from chatballs.ai.models import AgentTool
        from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider

        self.bind_session()
        detail = Integration.objects.create(
            organization=self.organization, kind=IntegrationKind.EXTERNAL_SERVER,
            provider=IntegrationProvider.HTTP, name="Order details",
            config={**self.tool.config, "tool_name": "get_my_order",
                    "url": "https://shop.example.test/order/{id}",
                    "parameters": [*self.tool.config["parameters"],
                                   {"name": "id", "type": "string", "required": True,
                                    "location": "path", "source": {"type": "ai"}}]},
        )
        AgentTool.objects.create(agent=self.agent, integration=detail)
        results = [{"orders": [{"id": "internal-42", "number": "51621"}]},
                   {"id": "internal-42", "status": "paid"}]
        provider = ScriptedProvider(calls(("get_my_orders", {})),
                                    calls(("get_my_order", {"id": "internal-42"})),
                                    says("Заказ оплачен."))
        with patch("chatballs.integrations.http_tool.fetch", side_effect=[
            ToolResponse(status=200, content_type="application/json", body=json.dumps(item).encode(), url="")
            for item in results
        ]) as fetch:
            incoming = self.run_turn(provider)
        payload = TurnDiagnostic.objects.get(message=incoming).payload
        self.assertEqual([call["name"] for call in payload["toolCalls"]], ["get_my_orders", "get_my_order"])
        self.assertEqual(payload["toolCalls"][1]["diagnostic"]["arguments"], {"id": "internal-42"})
        self.assertIn("/order/internal-42?", fetch.call_args_list[1].args[0])
        self.assertEqual(len(payload["rounds"]), 3)
        self.assertEqual(len(payload["rounds"][0]["request"]["messages"]) + 4,
                         len(payload["rounds"][2]["request"]["messages"]))

    def test_unsupported_model_and_disabled_tools_have_distinct_reasons(self):
        with patch("chatballs.ai.turn_tools.cached_tool_support", return_value=False):
            incoming = self.run_turn(ScriptedProvider(says("Ответ")))
        self.assertEqual(TurnDiagnostic.objects.get(message=incoming).payload["toolAvailability"][0]["reason"],
                         "model_does_not_support_tools")
        self.tool.is_active = False
        self.tool.save(update_fields=["is_active"])
        incoming = self.run_turn(ScriptedProvider(says("Ответ")))
        self.assertEqual(TurnDiagnostic.objects.get(message=incoming).payload["toolAvailability"][0]["reason"],
                         "integration_disabled")

    def test_historical_snapshot_does_not_change_when_configuration_changes(self):
        incoming = self.run_turn(ScriptedProvider(says("Ответ")))
        self.agent.name = "Changed agent"
        self.agent.save(update_fields=["name"])
        self.agent.tools.all().delete()
        payload = self.export().json()
        self.assertEqual(payload["turns"][0]["messageId"], incoming.id)
        self.assertEqual(payload["turns"][0]["agent"]["name"], "Support")
        self.assertEqual(payload["currentConfiguration"]["agent"]["name"], "Changed agent")
        self.assertEqual(payload["currentConfiguration"]["toolAvailability"][0]["reason"], "not_enabled_for_agent")

    def test_planning_failure_is_captured_and_handed_over(self):
        with patch("chatballs.ai.turn.prepare_chat", side_effect=ProviderError("provider unconfigured")):
            incoming = self.run_turn(ScriptedProvider(says("unused")))
        payload = TurnDiagnostic.objects.get(message=incoming).payload
        self.assertEqual(payload["state"], "planning_failed")
        self.assertTrue(payload["handoff"])

    def test_provider_failure_after_a_tool_round_is_captured(self):
        self.bind_session()
        with patch("chatballs.integrations.http_tool.fetch", return_value=ToolResponse(
            status=200, content_type="application/json", body=b'{}', url="",
        )):
            incoming = self.run_turn(ScriptedProvider(calls(("get_my_orders", {})),
                                                    ProviderError("provider failed session_token=" + SITE_SECRET)))
        payload = TurnDiagnostic.objects.get(message=incoming).payload
        self.assertEqual(payload["state"], "failed")
        self.assertTrue(payload["handoff"])
        self.assertNotIn(SITE_SECRET, json.dumps(payload))
        self.assertTrue(self.conversation.messages.filter(author_type=MessageAuthor.AI).exists())

    def test_diagnostic_storage_error_does_not_lose_the_customer_reply(self):
        with patch("chatballs.ai.diagnostic_capture.TurnDiagnostic.objects.update_or_create",
                   side_effect=RuntimeError("storage unavailable")):
            incoming = self.run_turn(ScriptedProvider(says("Заказ найден.")))
        self.assertFalse(TurnDiagnostic.objects.filter(message=incoming).exists())
        self.assertTrue(self.conversation.messages.filter(author_type=MessageAuthor.AI,
                                                        text="Заказ найден.").exists())

    def test_failed_planning_traces_are_also_pruned_and_deleted_with_the_dialog(self):
        from chatballs.ai.diagnostic_capture import record_planning_failure
        from chatballs.ai.diagnostic_storage import RETAINED_TURNS
        from chatballs.ai.pseudonymization import Pseudonymizer
        from chatballs.conversations.models import Message

        for _ in range(RETAINED_TURNS + 1):
            incoming = Message.objects.create(conversation=self.conversation,
                                              author_type=MessageAuthor.CONTACT)
            record_planning_failure(incoming, self.agent, self.conversation, Pseudonymizer(),
                                    ProviderError("unconfigured"))
        self.assertEqual(TurnDiagnostic.objects.filter(message__conversation=self.conversation).count(),
                         RETAINED_TURNS)
        self.conversation.delete()
        self.assertEqual(TurnDiagnostic.objects.count(), 0)
