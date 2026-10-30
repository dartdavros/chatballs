"""Совместимый мост к существующим HTTP/MCP (SPEC-0037 R-5, R-29)."""

from __future__ import annotations

from chatballs.ai.agent_tools_testing import AgentToolsTestCase
from chatballs.ai.tool_models import AgentTool
from chatballs.integrations.adapters.contracts import Effect, OperationContext, ResultState
from chatballs.integrations.adapters.legacy import bridge_descriptor
from chatballs.integrations.external_server_testing import order_status
from chatballs.integrations.models import (
    Integration,
    ServiceConnectionSettings,
    ToolReadOnlyConfirmation,
)


class LegacyBridgeTests(AgentToolsTestCase):
    def _integration(self, payload: dict) -> Integration:
        return Integration.objects.get(id=payload["id"])

    def test_mcp_tools_keep_their_read_and_write_nature(self) -> None:
        descriptor = bridge_descriptor(self._integration(self.mcp))

        effects = {operation.protocol["mcp"]["tool"]: operation.effect for operation in descriptor.operations}
        self.assertEqual(effects["get_order_status"], Effect.READ)
        # Запись не выдаётся за чтение и не требует ложной отметки.
        self.assertNotEqual(effects["cancel_order"], Effect.READ)
        self.assertFalse(descriptor.listed)

    def test_confirmed_tool_is_read_by_the_bridge_without_new_rights(self) -> None:
        self._confirm()

        descriptor = bridge_descriptor(self._integration(self.mcp))

        cancel = next(item for item in descriptor.operations if item.protocol["mcp"]["tool"] == "cancel_order")
        self.assertEqual(cancel.effect, Effect.READ)

    def test_bridge_neither_copies_secrets_nor_changes_permissions(self) -> None:
        self._enable((self.mcp, "get_order_status"))
        before = (
            list(AgentTool.objects.values_list("agent_id", "integration_id", "tool_name")),
            list(ToolReadOnlyConfirmation.objects.values_list("tool_name", "revoked_at")),
        )
        server = self._integration(self.mcp)
        secrets = (server.secret, server.secret_headers)

        bridge_descriptor(server)
        bridge_descriptor(self._integration(self.http))

        server.refresh_from_db()
        self.assertEqual((server.secret, server.secret_headers), secrets)
        self.assertFalse(ServiceConnectionSettings.objects.exists())
        self.assertEqual(
            before,
            (
                list(AgentTool.objects.values_list("agent_id", "integration_id", "tool_name")),
                list(ToolReadOnlyConfirmation.objects.values_list("tool_name", "revoked_at")),
            ),
        )

    def test_http_request_effect_follows_its_method(self) -> None:
        reading = bridge_descriptor(self._integration(self.http)).operations[0]
        writing = bridge_descriptor(self._integration(self._http("Отмена заказа", method="POST"))).operations[0]

        self.assertEqual(reading.effect, Effect.READ)
        self.assertEqual(writing.effect, Effect.CREATE)

    def test_bridge_call_uses_the_stored_server(self) -> None:
        server = self._integration(self.http)
        operation = bridge_descriptor(server).operations[0]
        context = OperationContext(organization_id=server.organization_id, connection=server, settings={}, credentials={})

        result = operation.handlers.execute(context, operation, {"order_number": ".."})

        # Параметр пути проверяет прежний исполнитель запроса, без сети.
        self.assertEqual((result.state, result.error_code), (ResultState.FAILED, "arguments"))

    def test_mcp_write_tool_runs_through_the_stored_server_without_a_read_only_mark(self) -> None:
        server = self._integration(self.mcp)
        operation = next(item for item in bridge_descriptor(server).operations if item.protocol["mcp"]["tool"] == "cancel_order")
        context = OperationContext(organization_id=server.organization_id, connection=server, settings={}, credentials={})

        result = operation.handlers.execute(context, operation, {"order_number": "A-1"})

        self.assertEqual((result.state, result.data), (ResultState.COMPLETED, "Заказ в пути"))
        self.assertFalse(ToolReadOnlyConfirmation.objects.exists())
        # Сервер требует исходный секретный заголовок: вызов прошёл с ним, хотя
        # его никуда не копировали.
        self.assertIn("tools/call", self.server.methods)

    def test_settings_payload_of_old_servers_is_unchanged(self) -> None:
        self.assertEqual(order_status()["method"], self.http["externalServer"]["method"])
