"""Existing Django test database only; no services or accounts in the dev installation."""

from unittest.mock import patch

from chatballs.ai.models import AgentTool, AIAgent, AIAgentStatus
from chatballs.conversations.ai_turn import run_requested_turn
from chatballs.conversations.models import AiTurnState, Message, MessageAuthor
from chatballs.conversations.test_chat_extras import ChatExtrasTestCase
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.testing import system_tenant_context


class DiagnosticTestCase(ChatExtrasTestCase):
    def setUp(self):
        super().setUp()
        self.agent = AIAgent.objects.create(channel=self.channel, name="Support",
                                           status=AIAgentStatus.ACTIVE, model="scripted")
        self.web = Integration.objects.create(
            organization=self.organization, channel=self.channel, name="Website",
            kind=IntegrationKind.MESSENGER, provider=IntegrationProvider.WEB,
            config={"fields": [{"key": "session_token", "type": "text",
                                "label": "Session", "ai_access": "hidden"}]},
        )
        self.conversation.connection = self.web
        self.conversation.save(update_fields=["connection"])
        self.tool = Integration.objects.create(
            organization=self.organization, kind=IntegrationKind.EXTERNAL_SERVER,
            provider=IntegrationProvider.HTTP, name="Orders",
            config={"tool_name": "get_my_orders", "method": "GET",
                    "url": "https://shop.example.test/orders",
                    "parameters": [{"name": "session_token", "type": "string",
                                    "required": True, "location": "query",
                                    "source": {"type": "web_field", "integration_id": self.web.id,
                                               "key": "session_token"}}]},
        )
        AgentTool.objects.create(agent=self.agent, integration=self.tool)

    def run_turn(self, provider):
        incoming = Message.objects.create(
            conversation=self.conversation, author_type=MessageAuthor.CONTACT,
            text="Какой статус заказа 51621?", ai_turn_state=AiTurnState.PENDING,
        )
        with (patch("chatballs.ai.invocation.get_provider", return_value=provider),
              patch("chatballs.conversations.transports.send_reply", return_value=True)):
            run_requested_turn({"messageId": incoming.id}, system_tenant_context(self.organization))
        return incoming

    def export(self, client=None):
        return (client or self.admin_client).get(
            f"/api/v1/conversations/{self.conversation.id}/diagnostic/"
        )
