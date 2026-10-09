"""A portable, versioned diagnostic file; historical and current state stay separate."""

from django.conf import settings
from django.utils import timezone

from chatballs.ai.diagnostic_models import TurnDiagnostic
from chatballs.ai.diagnostic_redaction import DiagnosticRedactor, integration_secrets
from chatballs.ai.diagnostic_snapshot import diagnostic_context
from chatballs.ai.diagnostic_storage import RETAINED_TURNS
from chatballs.ai.turn import turn_pseudonymizer
from chatballs.ai.turn_tools import plan_turn_tools
from chatballs.conversations.models import AiTurnState, ContactFieldValue, MessageAuthor
from chatballs.integrations.models import Integration

MAX_MESSAGES = 2000
MAX_TRACES = RETAINED_TURNS


def conversation_diagnostic(conversation):
    pseudonymizer = turn_pseudonymizer(conversation)
    integrations = Integration.objects.filter(organization_id=conversation.organization_id)
    secrets = integration_secrets(integrations)
    secrets.extend(str(value) for value in ContactFieldValue.objects.filter(
        organization_id=conversation.organization_id, contact_id=conversation.contact_id,
    ).values_list("value", flat=True))
    redactor = DiagnosticRedactor(pseudonymizer, secrets)
    agent = getattr(conversation.channel, "ai_agent", None)
    current = None
    if agent is not None:
        client, _, snapshot = diagnostic_context(agent, conversation, pseudonymizer)
        plan_turn_tools(agent=agent, conversation=conversation, client=client,
                        decisions=snapshot["toolAvailability"])
        current = redactor.clean(snapshot)
    latest = list(conversation.messages.order_by("-created_at", "-id")[:MAX_MESSAGES])
    rows = list(reversed(latest))
    traces = list(TurnDiagnostic.objects.filter(
        organization_id=conversation.organization_id, message__conversation=conversation,
        message_id__in=[message.id for message in rows],
    ).order_by("-message_id")[:MAX_TRACES])
    by_message = {trace.message_id: trace for trace in traces}
    missing = [message.id for message in rows
               if message.author_type == MessageAuthor.CONTACT
               and message.ai_turn_state != AiTurnState.NONE and message.id not in by_message]
    messages = [
        {"id": message.id, "createdAt": message.created_at.isoformat(),
         "author": message.author_type, "kind": message.kind,
         "text": redactor.text(message.text or message.transcript),
         "event": message.system_event, "eventParams": redactor.clean(message.system_params),
         "aiTurnState": message.ai_turn_state}
        for message in rows
    ]
    return {
        "format": "chatballs.conversation-diagnostic", "schemaVersion": 1,
        "exportedAt": timezone.now().isoformat(), "version": settings.CHATBALLS_VERSION,
        "conversation": {"id": conversation.id, "channelId": conversation.channel_id,
                         "connectionId": conversation.connection_id,
                         "lifecycle": conversation.lifecycle, "controlMode": conversation.control_mode},
        "limits": {"messages": MAX_MESSAGES, "turns": MAX_TRACES,
                   "messagesTruncated": conversation.messages.count() > MAX_MESSAGES,
                   "textTruncated": redactor.truncated},
        "currentConfiguration": current,
        "messages": messages,
        "turns": [{"messageId": trace.message_id, **trace.payload} for trace in reversed(traces)],
        "coverage": {"messagesWithoutTrace": missing,
                     "historicalConfigurationReconstructed": False,
                     "currentConfigurationIsHistorical": False,
                     "secretsIncluded": False, "attachmentsIncluded": False},
    }
