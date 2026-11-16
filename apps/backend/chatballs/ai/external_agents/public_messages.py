"""Only stored public message content crosses the external-agent boundary."""

from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.file_access import grant_message
from chatballs.ai.external_agents.payloads import utc
from chatballs.conversations.audience_managers import without_suppressed
from chatballs.conversations.models import (
    Message,
    MessageAuthor,
    MessageKind,
    TranscriptStatus,
)

AUTHORS = {MessageAuthor.CONTACT: "customer", MessageAuthor.OPERATOR: "employee", MessageAuthor.AI: "agent"}


def public_message(message, row=None):
    if (message.system_event or message.audio and message.kind != MessageKind.VOICE
            or message.attachment and message.kind != MessageKind.FILE):
        raise ValueError("unsupported_content")
    item = {"id": str(message.pk), "author": AUTHORS[message.author_type],
            "createdAt": utc(message.created_at), "wasVoice": False}
    if message.kind == MessageKind.FILE and row is not None:
        item["content"] = grant_message(row, message)
    elif message.format_version or message.template_snapshot:
        saved = message.template_snapshot
        item["content"] = {"type": "formatted", "text": message.text,
                           "templateId": saved.get("id") if saved.get("revision") else None,
                           "templateRevision": saved.get("revision")}
    elif message.kind == MessageKind.CONTACT_REQUEST:
        item["content"] = {"type": "contact_request", "text": message.text}
    elif message.kind == MessageKind.VOICE:
        if message.transcript_status != TranscriptStatus.READY or not message.transcript.strip():
            raise ValueError("history_content_unavailable")
        item.update(content={"type": "text", "text": message.transcript}, wasVoice=True,
                    source={"kind": "voice", "durationSeconds": message.duration_seconds})
    elif message.kind == MessageKind.CONTACT:
        item["content"] = {"type": "contact", "text": message.text}
    elif message.kind or message.audio:
        raise ValueError("unsupported_content")
    else:
        if not message.text:
            raise ValueError("history_content_unavailable")
        item["content"] = {"type": "text", "text": message.text}
    return item


def trigger_payload(message, seed, row=None):
    if seed["kind"] != message.kind or seed["text"] != message.text:
        raise ValueError("unsupported_content")
    public = public_message(message, row)
    value = public["content"]
    is_file = value["type"] in ("file", "image")
    return {"messageId": public["id"], "createdAt": public["createdAt"],
            "type": value["type"], "text": value.get("text", value.get("caption", "")),
            "wasVoice": public["wasVoice"], "attachments": [value] if is_file else [],
            **({"source": public["source"]} if public["wasVoice"] else {})}


def history_messages(row):
    messages = list(without_suppressed(Message.including_tests.filter(
        conversation_id=row.conversation_id, organization_id=row.conversation.organization_id,
        author_type__in=AUTHORS,
    ).exclude(author_type=MessageAuthor.CONTACT, pk__gte=row.trigger_id)))
    replies = {item.message_id: (item.delivery.request.sequence, item.position)
               for item in ExternalAgentDeliveryItem.objects.filter(
                   delivery__request__conversation_id=row.conversation_id,
                   delivery__request__sequence__lt=row.sequence,
               ).select_related("delivery__request")}

    def order(message):
        fact = message.ai_delivery.get("externalDelivery")
        if fact:
            return fact["sequence"], 1, fact["position"], message.pk
        if message.pk in replies:
            sequence, position = replies[message.pk]
            return sequence, 1, position, message.pk
        if message.ai_reply_to_id:
            return message.ai_reply_to_id, 1, 0, message.pk
        return message.pk, 0, 0, message.pk

    return [public_message(message, row) for message in sorted(messages, key=order)]
