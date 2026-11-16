"""Closed OpenAPI schemas and identical body/header idempotency identities."""

from uuid import UUID

from rest_framework.response import Response

from chatballs.ai.external_agents import handoff_request, proactive
from chatballs.ai.external_agents.auth import authenticated
from chatballs.ai.external_agents.contracts import parse
from chatballs.ai.external_agents.views import ProtocolView


class OperationView(ProtocolView):
    def post(self, request, connection_id, conversation_id):
        body = parse("result.yaml", self.body_schema, request.body)
        try:
            if UUID(request.headers.get("Idempotency-Key", "")) != UUID(body[self.identifier]):
                raise ValueError
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError("invalid_request") from error
        if not body["agentId"].isascii() or not body["agentId"].isdigit() or not 0 < int(body["agentId"]) < 2**63:
            raise ValueError("invalid_request")
        with authenticated(request.headers.get("Authorization")) as (context, connection):
            self.check_connection(connection, connection_id)
            ack, status = self.service.accept(context, connection, conversation_id, body)
        return Response(ack, status=status)


class MessagesView(OperationView):
    body_schema, identifier, service = "ProactiveMessages", "deliveryId", proactive


class HandoffView(OperationView):
    body_schema, identifier, service = "HandoffRequest", "eventId", handoff_request
