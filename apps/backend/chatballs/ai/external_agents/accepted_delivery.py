"""One publication and delivery transition for replies and proactive batches."""

from uuid import uuid4

from chatballs.ai.external_agents.batch_delivery import publish
from chatballs.ai.external_agents.delivery_models import ExternalAgentDelivery
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.state import DELIVER, finish, schedule


def accept_delivery(context, row, conversation, normalized, *, delivery_id=None, proactive=False):
    delivery = ExternalAgentDelivery.objects.create(request=row, **({"public_id": delivery_id} if delivery_id else {}))
    route = open_payload(row.seed_ciphertext)["route"]
    if conversation.is_test:
        from chatballs.ai.external_agents.test_delivery import accept_panel

        accept_panel(conversation, row, context)
    web = route["representation"] == "html" and not route.get("sourceLetterId")
    item_state = "transport_accepted" if web else "queued"
    items = publish(context, row, conversation, delivery, normalized, route, item_state)
    ack = {"version": "1", "requestId": None if proactive else str(row.public_id), "receiptId": str(uuid4()),
           "state": item_state, "deliveryId": str(delivery.public_id), "items": items}
    if web:
        conversation.expected_responder = "CUSTOMER"
        conversation.save(update_fields=["expected_responder"])
        finish(row, context)
    else:
        row.state, row.lease_until = "delivering", None
        row.save(update_fields=["state", "lease_until"])
        schedule(context, row.conversation_id, event_type=DELIVER)
    return ack, 200 if web else 202
