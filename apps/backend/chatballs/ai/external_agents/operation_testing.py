"""Protocol requests against real services inside the isolated test database."""

import struct
import zlib
from uuid import uuid4

from chatballs.ai.external_agents.config_models import ExternalAgentBinding


def image_bytes():
    def chunk(kind, body):
        return struct.pack("!I", len(body)) + kind + body + struct.pack("!I", zlib.crc32(kind + body))

    header = struct.pack("!IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(b"\0" + b"\xff\0\0" * 2 + b"\0" + b"\xff\0\0" * 2))
            + chunk(b"IEND", b""))


class OperationData:
    def prepare_session(self, *, proactive=True, complete=True):
        ExternalAgentBinding.objects.filter(agent=self.agent).exclude(proactive_enabled=proactive).update(proactive_enabled=proactive)
        row = self.request()
        if complete:
            self.claim()
            self.accept(row, self.result(row))
            self.deliver()
        row.session.refresh_from_db()
        self.session = row.session
        return row

    def operation_body(self, operation="messages", **values):
        body = {"version": "1", "agentId": str(self.agent.pk),
                "authorizationId": str(self.session.authorization_id),
                "externalSessionId": self.session.external_session_id or None}
        if operation == "messages":
            body.update(deliveryId=str(uuid4()), messages=[
                {"itemId": str(uuid4()), "content": {"type": "text", "text": "Initiative"}}])
        else:
            body.update(eventId=str(uuid4()), reasonCode="agent_requested", summary="Private employee context")
        return {**body, **values}

    def post_operation(self, body, operation="messages", *, conversation_id=None, **headers):
        identifier = body["deliveryId" if operation == "messages" else "eventId"]
        headers.setdefault("HTTP_IDEMPOTENCY_KEY", identifier)
        headers.setdefault("HTTP_AUTHORIZATION", "Bearer " + self.created["incomingKey"])
        return self.client.post(
            f"/api/v1/external-agent/connections/{self.connection.pk}/conversations/"
            f"{conversation_id or self.conversation.pk}/{operation}/", body, format="json", **headers)
