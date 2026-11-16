"""Public text delivery with a durable pre-send marker and conservative unknown."""

from django.http import Http404
from django.utils import timezone

from chatballs.ai.execution_policy import execution_guard
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.formatted_replies import TemplateConflict
from chatballs.ai.external_agents.handoff import handoff
from chatballs.ai.external_agents.normalization import current as content_current
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.send_guards import delivery_current, delivery_handoff
from chatballs.ai.external_agents.state import (
    DELIVER,
    applicable,
    finish,
    head,
    lock_conversation,
    schedule,
)
from chatballs.ai.provider.base import ProviderRejected
from chatballs.conversations import transports
from chatballs.conversations.models import ExpectedResponder
from chatballs.conversations.transports.email import prepare_text
from chatballs.conversations.transports.email_smtp import continuation_message, deliver_message
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic


def aggregate(items):
    states = {item.state for item in items}
    return "queued" if "queued" in states else next(iter(states)) if len(states) == 1 else "partial"


def claim(context, conversation_id):
    conversation = lock_conversation(context, conversation_id)
    if conversation is None:
        return None
    row = head(conversation_id)
    if row is None or row.state != "delivering":
        return None
    items = list(row.externalagentdelivery.items.select_for_update().select_related("message"))
    permitted = applicable(row, context)
    if not permitted:
        for item in items:
            if item.state == "queued":
                item.state = "unknown" if item.sending else "suppressed"
                item.reason_code = "control_revoked"
                item.save(update_fields=["state", "reason_code"])
        if timezone.now() >= row.deadline_at and applicable(row, context, deadline=False):
            handoff(conversation, context, operation_id=row.public_id)
        finish(row, context, reason="control_revoked")
        return None
    if any(item.state == "unknown" or item.sending for item in items):
        for item in items:
            if item.sending and item.state == "queued":
                item.state = "unknown"
                item.save(update_fields=["state"])
        schedule(context, conversation_id, at=row.deadline_at, event_type=DELIVER)
        return None
    pending = next((item for item in items if item.state == "queued"), None)
    if pending is None:
        if any(item.state == "failed" for item in items):
            handoff(conversation, context, operation_id=row.public_id)
            finish(row, context, reason="delivery_failed")
            return None
        conversation.expected_responder = ExpectedResponder.CUSTOMER
        conversation.save(update_fields=["expected_responder"])
        finish(row, context)
        return None
    try:
        content_current(pending.message, row)
    except (Http404, ValueError, TemplateConflict):
        pending.state, pending.reason_code = "suppressed", "content_unavailable"
        pending.save(update_fields=["state", "reason_code"])
        schedule(context, conversation_id, event_type=DELIVER)
        return None
    pending.sending = True
    pending.save(update_fields=["sending"])
    # Crash before/after channel acceptance must never cause a blind resend.
    schedule(context, conversation_id, at=row.deadline_at, event_type=DELIVER)
    seed = open_payload(row.seed_ciphertext)
    route = seed["route"]
    connection = Integration.objects.get(pk=route["connectionId"])
    connection.organization = context.organization
    letter = getattr(pending.message, "email_transport", None)
    outgoing = continuation_message(letter) if letter else None
    if outgoing is None and connection.provider == "EMAIL":
        outgoing = prepare_text(connection, target=route["chatId"], text=pending.message.text, meta=route.get("mailMeta", {}))
        # Each batch item is an independent letter, never a duplicate Message-ID.
        from email.utils import make_msgid

        outgoing["Message-ID"] = make_msgid()
    attachment = None
    if pending.message.attachment:
        with pending.message.attachment.open("rb") as stream:
            attachment = (stream.read(), pending.message.attachment_name, pending.message.attachment_content_type)
        if outgoing is not None and not letter:
            data, filename, mime = attachment
            main, sub = mime.split("/", 1)
            outgoing.add_attachment(data, maintype=main, subtype=sub, filename=filename)
    return (pending.pk, connection, route["chatId"], seed["userId"], pending.message.text,
            outgoing, pending.message.kind, attachment)


def send(connection, chat_id, user_id, text, outgoing=None, kind="", attachment=None):
    if connection is None or not connection.is_active:
        return "failed"
    if connection.provider == "WEB":
        return "transport_accepted"
    if connection.provider == "EMAIL":
        result = deliver_message(connection, outgoing)
        return {"SMTP_ACCEPTED": "transport_accepted", "FAILED": "failed"}.get(result.state, "unknown")
    try:
        if attachment:
            data, filename, mime = attachment
            accepted = transports.send_file(connection, chat_id=chat_id, user_id=user_id,
                content=data, filename=filename, content_type=mime, caption=text)
        elif kind == "contact_request":
            accepted = transports.send_contact_request(connection, chat_id=chat_id, user_id=user_id, text=text)
        else:
            accepted = transports.send_reply(connection, chat_id=chat_id, user_id=user_id, text=text)
    except (OSError, TimeoutError):
        return "unknown"
    # Existing boolean transports collapse negative replies and lost ACKs.
    # False cannot establish non-acceptance; never promise a safe resend.
    return "transport_accepted" if accepted else "unknown"


def run(context, conversation_id):
    with tenant_atomic(context):
        work = claim(context, conversation_id)
    if work is None:
        return
    item_id, connection, chat_id, user_id, text, outgoing, kind, attachment = work
    try:
        with execution_guard(lambda: delivery_current(item_id, context, conversation_id),
                             handoff=lambda: delivery_handoff(item_id, context, conversation_id)):
            outcome = send(connection, chat_id, user_id, text, outgoing, kind, attachment)
    except ProviderRejected:
        outcome = "suppressed"
    with tenant_atomic(context):
        if lock_conversation(context, conversation_id) is None:
            return
        item = ExternalAgentDeliveryItem.objects.select_for_update().filter(pk=item_id).first()
        if item is None:
            return
        item.state, item.sending = outcome, False
        item.save(update_fields=["state", "sending"])
        item.delivery.save(update_fields=["updated_at"])
        schedule(context, conversation_id, event_type=DELIVER)
