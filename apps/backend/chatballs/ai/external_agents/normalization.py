"""Validate a complete ordered set, producing native Message fields without effects."""

from uuid import UUID

from chatballs.ai.external_agents.content_constraints import check_text, constraints
from chatballs.ai.external_agents.contracts import validate
from chatballs.ai.external_agents.file_access import verify
from chatballs.ai.external_agents.formatted_replies import prepare
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.i18n import customer_language, t
from chatballs.integrations.models import Integration


def normalize(row, items):
    if len({UUID(item["itemId"]) for item in items}) != len(items):
        raise ValueError("invalid_request")
    limits = constraints(row)
    route = open_payload(row.seed_ciphertext)["route"]
    transport = None if row.conversation.is_test else Integration.objects.get(pk=route["connectionId"])
    result = []
    for item in items:
        validate("messages.yaml", "OutgoingItem", item)
        content = item["content"]
        kind = content["type"]
        if kind not in limits["types"]:
            raise ValueError("channel_restricted")
        if kind == "text":
            fields = {"text": content["text"]}
        elif kind == "formatted":
            fields = prepare(row, content, representation=route["representation"])
        elif kind == "contact_request":
            key = "conversations.contact_request_web" if transport is None or transport.provider == "WEB" else "conversations.contact_request"
            fields = {"kind": kind, "text": t(key, language=customer_language(row.conversation.organization))}
        else:
            record = verify(row.session, content)
            if record.size > limits["maxFileBytes"]:
                raise ValueError("channel_restricted")
            fields = {"kind": "file", "text": content["caption"], "attachment": record.file.name,
                      "attachment_name": record.filename, "attachment_size": record.size,
                      "attachment_content_type": record.mime_type,
                      "ai_delivery": {"externalFileId": str(record.public_id)}}
        check_text(fields["text"], row, caption=kind in ("file", "image"))
        result.append((item["itemId"], fields))
    return result


def current(message, row):
    from chatballs.ai.external_agents.file_access import content, load, verify
    from chatballs.ai.external_agents.formatted_replies import TemplateConflict
    from chatballs.ai.external_agents.formatted_replies import current as template_current

    if not template_current(message, row):
        raise TemplateConflict()
    if message.attachment:
        record = load(row.session, message.ai_delivery.get("externalFileId"))
        if (record.file.name != message.attachment.name or record.size != message.attachment_size
                or record.filename != message.attachment_name or record.mime_type != message.attachment_content_type):
            raise ValueError("invalid_request")
        verify(row.session, content(record, message.text))
    check_text(message.text, row, caption=bool(message.attachment))
    return True
