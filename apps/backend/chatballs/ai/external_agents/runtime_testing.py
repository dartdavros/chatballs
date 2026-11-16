"""Test-database setup and controlled transport outcomes; no external service."""

import json
from unittest.mock import patch
from uuid import uuid4

from chatballs.ai.external_agents import delivery, dispatch, ingress
from chatballs.ai.external_agents.config_bindings import select_execution
from chatballs.ai.external_agents.config_models import ExternalAgentConnection
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.testing import ConfigurationData
from chatballs.conversations.ai_turn_state import request_ai_turn
from chatballs.conversations.models import Contact, Conversation, Message
from chatballs.integrations.adapters.transport import TransportResponse
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic


class RuntimeData(ConfigurationData):
    def setUp(self):
        super().setUp()
        self.created = self.connect()
        self.connection = ExternalAgentConnection.objects.get(pk=self.created["connection"]["id"])
        self.bind(self.connection.pk)
        select_execution(self.context, self.agent.pk, "external")
        self.agent.refresh_from_db()
        self.channel.ai_agent = self.agent
        self.messaging = Integration.objects.create(organization=self.organization, channel=self.channel,
            kind="MESSENGER", provider="TELEGRAM", name="Test transport", secret="test-only")
        self.contact = Contact.objects.create(organization=self.organization, name="Customer")
        self.conversation = Conversation.objects.create(organization=self.organization, channel=self.channel, contact=self.contact,
                                                       connection=self.messaging, external_chat_id="test-chat")
        self.enterContext(patch("chatballs.ai.external_agents.context.public_base_url", return_value="https://chatballs.example.invalid"))
        self.sender = self.enterContext(patch("chatballs.conversations.transports.send_reply", return_value=True))

    def request(self, text="Question", **fields):
        with tenant_atomic(self.context):
            message = Message.objects.create(conversation=self.conversation, author_type="CONTACT", text=text, **fields)
            request_ai_turn(message=message, user_id="test-user", context=self.context)
            return ExternalAgentRequest.objects.get(trigger=message)

    def claim(self):
        with tenant_atomic(self.context):
            return dispatch.claim(self.context, self.conversation.pk)

    def settle(self, work, body=None, status=200):
        response = None if body is None else TransportResponse(
            status=status, content_type="application/json", url="", body=json.dumps(body).encode())
        with tenant_atomic(self.context):
            dispatch.settle(work, self.context, response)

    def result(self, row, *, text="Answer", count=1):
        return {"version": "1", "requestId": str(row.public_id), "resultId": str(uuid4()),
                "status": "completed", "externalSessionId": "session-1", "outcome": {"type": "reply", "messages": [
                    {"itemId": str(uuid4()), "content": {"type": "text", "text": text}} for _ in range(count)]}}

    def accept(self, row, result):
        with tenant_atomic(self.context):
            return ingress.accept(self.context, self.connection, str(row.public_id), result)

    def deliver(self, times=2):
        for _ in range(times):
            delivery.run(self.context, self.conversation.pk)

    def callback(self, row, result, **headers):
        return self.client.post(
            f"/api/v1/external-agent/connections/{self.connection.pk}/requests/{row.public_id}/result/",
            result, format="json", HTTP_AUTHORIZATION="Bearer " + self.created["incomingKey"], **headers)
