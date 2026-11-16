"""Separate structured employee request with a narrow lost-ACK replay exception."""

from chatballs.ai.external_agents.auth import _current
from chatballs.ai.external_agents.contracts import validate
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.handoff import handoff
from chatballs.ai.external_agents.ingress import control_ack
from chatballs.ai.external_agents.operations import identity, remember
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.state import FINAL, cancel
from chatballs.conversations.domain_events import operation_key


def accept(context, connection, conversation_id, body):
    session, conversation, previous, hashed = identity(context, connection, conversation_id, body, "handoff")
    if previous:
        return previous.ack, 200
    operation_id = operation_key("external-handoff", f"{session.pk}:{conversation_id}:{body['eventId']}")
    handoff(conversation, context, operation_id=operation_id, summary=body["summary"])
    for row in ExternalAgentRequest.objects.filter(conversation=conversation).exclude(state__in=FINAL):
        for item in ExternalAgentDeliveryItem.objects.filter(delivery__request=row, state="queued"):
            item.state = "unknown" if item.sending else "suppressed"
            item.reason_code = "control_revoked"
            item.save(update_fields=["state", "reason_code"])
        cancel(row, context, "control_revoked")
    _, _, _, _, versions = _current(context, connection, session.agent_id, conversation_id, require_control=False)
    ack = control_ack(None, "handed_off", body["reasonCode"])
    ack["requestId"] = None
    validate("receipts.yaml", "ControlReceipt", ack)
    remember(session, body, "handoff", hashed, ack, post_versions=versions)
    return ack, 200
