"""Safe panel state, with no recovery payloads, credentials or foreign context."""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.ui_projection import message_status
from chatballs.conversations.models import Message


def request_state(row):
    if row is None:
        return "idle"
    states = list(row.externalagentdelivery.items.values_list("state", flat=True)) if hasattr(row, "externalagentdelivery") else []
    if "unknown" in states:
        return "partial" if "transport_accepted" in states else "unknown"
    if row.state in ("cancelled", "terminal"):
        return "error" if row.reason_code else "ready"
    return "longWaiting" if (timezone.now() - row.created_at).total_seconds() > row.session.agent.external_binding.ordinary_timeout else "waiting"


def project(scope):
    from chatballs.ai.external_agents.test_scope import active_scope

    try:
        active_scope(scope.conversation, scope.agent, require_control=False)
        available = True
    except PermissionDenied:
        available = False
    row = ExternalAgentRequest.objects.filter(conversation_id=scope.conversation_id).select_related(
        "session__agent__external_binding").order_by("-sequence", "-pk").first()
    state = request_state(row) if available else "blocked"
    if scope.conversation.control_mode == "HUMAN" and available:
        state = "handoff"
    messages = []
    for message in Message.including_tests.filter(conversation_id=scope.conversation_id).order_by("pk"):
        if message.author_type not in ("CONTACT", "AI"):
            continue
        if message.author_type == "AI" and message_status(message).get("externalDelivery", {}).get("state") != "transport_accepted":
            continue
        messages.append({"id": message.pk, "role": "user" if message.author_type == "CONTACT" else "assistant",
                         "text": message.text, "createdAt": message.created_at.isoformat(),
                         "formatVersion": message.format_version, "presentation": message.presentation,
                         "kind": message.kind, "filename": message.attachment_name,
                         "fileUrl": f"files/{message.pk}/" if message.attachment else None})
    return {"id": str(scope.public_id), "available": bool(available), "state": state, "messages": messages}
