"""Admit initiative only into an existing idle conversation; reuse native delivery."""

from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone

from chatballs.ai.external_agents.accepted_delivery import accept_delivery
from chatballs.ai.external_agents.contracts import validate
from chatballs.ai.external_agents.delivery_models import ExternalAgentDelivery
from chatballs.ai.external_agents.ingress import Conflict
from chatballs.ai.external_agents.normalization import normalize
from chatballs.ai.external_agents.operations import identity, remember
from chatballs.ai.external_agents.payloads import open_payload, seal
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.state import FINAL
from chatballs.conversations.ai_reply_delivery import reply_route
from chatballs.conversations.models import Message
from chatballs.integrations.models import Integration


def accept(context, connection, conversation_id, body):
    session, conversation, previous, hashed = identity(context, connection, conversation_id, body, "messages")
    if previous:
        return previous.ack, 200
    if ExternalAgentDelivery.objects.filter(public_id=body["deliveryId"]).exists():
        raise Conflict(code="idempotency_conflict")
    if (ExternalAgentRequest.objects.filter(conversation=conversation).exclude(state__in=FINAL).exists()
            or Message.including_tests.filter(conversation=conversation, author_type="CONTACT",
                                      ai_turn_state__in=["PENDING", "RUNNING"]).exists()):
        raise Conflict(code="conversation_busy")
    # Routing and recipient come only from the saved native conversation/trigger.
    source = ExternalAgentRequest.objects.filter(session=session, trigger__isnull=False).exclude(
        seed_ciphertext="").order_by("-sequence").first()
    user_id = open_payload(source.seed_ciphertext)["userId"] if source else conversation.external_chat_id
    trigger = Message.including_tests.filter(conversation=conversation, author_type="CONTACT").order_by("-pk").first()
    route = reply_route(SimpleNamespace(message=trigger, conversation=conversation, user_id=user_id))
    if conversation.is_test:
        from chatballs.ai.external_agents.test_scope import test_route

        route = test_route(conversation)
    if not conversation.is_test and not route["chatId"] and not user_id:
        raise ValueError("channel_restricted")
    if not conversation.is_test:
        transport = Integration.objects.get(pk=route["connectionId"])
        route["transportVersion"] = transport.runtime_revision
    binding = session.agent.external_binding
    timeout = binding.long_timeout if binding.processing_mode == "long" else binding.ordinary_timeout
    now = timezone.now()
    # No fake incoming Message: the normal FIFO checkpoint has a nullable trigger.
    row = ExternalAgentRequest(session=session, conversation=conversation,
        authorization_id=session.authorization_id, authorization_versions=session.authorization_versions,
        sequence=Message.including_tests.filter(conversation=conversation).order_by("-pk").values_list("pk", flat=True).first() or 1,
        deadline_at=now + timedelta(seconds=min(timeout, binding.maximum_timeout)), next_at=now,
        active=True, state="delivering", seed_ciphertext=seal({"route": route, "userId": user_id}))
    normalized = normalize(row, body["messages"])
    row.save()
    ack, status = accept_delivery(context, row, conversation, normalized,
        delivery_id=body["deliveryId"], proactive=True)
    validate("receipts.yaml", "DeliveryReceipt", ack)
    remember(session, body, "messages", hashed, ack)
    return ack, status
