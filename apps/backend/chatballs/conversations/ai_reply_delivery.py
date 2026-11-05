"""Persist the actual route; retries only deliver the already stored reply."""

from email.utils import make_msgid

from chatballs.ai.execution_version import configuration_version
from chatballs.conversations import transports
from chatballs.conversations.domain_events import operation_key, record_public_reply
from chatballs.conversations.email_facts import record_email_fact
from chatballs.conversations.email_thread_models import EmailThreadMessage
from chatballs.conversations.models import Message
from chatballs.conversations.transports.email import prepare_text
from chatballs.conversations.transports.email_smtp import continuation_message, deliver_message
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic


class AiDeliveryFailed(Exception):
    pass


def reply_route(turn):
    letter = getattr(turn.message, "email_transport", None)
    if letter is not None:
        return {"connectionId": letter.connection_id, "chatId": letter.thread.recipient,
                "userId": turn.user_id, "representation": "text", "sourceLetterId": letter.pk}
    connection = turn.conversation.connection
    route = {"connectionId": connection.pk if connection else None,
            "chatId": turn.conversation.external_chat_id, "userId": turn.user_id,
            "representation": "html" if connection and connection.provider == "WEB" else "text"}
    if connection and connection.provider == "EMAIL":
        route["mailMeta"] = {key: turn.conversation.transport_meta.get(key, "") for key in ("subject", "last_message_id")}
        route["messageId"] = make_msgid()
    return route


def bind_reply(turn, message, route):
    route["modeVersion"] = turn.mode_version
    route["controlVersion"] = turn.control_version
    route["agentId"] = turn.agent.pk
    route["agentVersion"] = configuration_version(turn.agent)
    if turn.message is not None and turn.message.ai_delivery.get("actionRuns"):
        route["actionRuns"] = turn.message.ai_delivery["actionRuns"]
    if getattr(turn, "site_event_launch_id", None) is not None:
        # WEB delivery is the committed history row read by the widget poll.
        route.update(siteEventLaunchId=turn.site_event_launch_id, sent=True)
    message.ai_reply_to = turn.message
    message.ai_delivery = route
    message.save(update_fields=["ai_reply_to", "ai_delivery"])
    if route.get("sourceLetterId"):
        source = EmailThreadMessage.objects.select_related("connection", "thread").get(pk=route["sourceLetterId"])
        EmailThreadMessage.objects.create(
            thread=source.thread, connection=source.connection, message=message, direction="OUTBOUND",
            mail_message_id=make_msgid(), in_reply_to=source.mail_message_id,
            references=[*source.references, source.mail_message_id][-30:],
            sender_address=source.recipient_address, recipient_address=source.sender_address or source.thread.recipient,
            subject=source.subject or source.thread.subject, mailbox_name=source.mailbox_name,
        )


def record_reply(message):
    letter = getattr(message, "email_transport", None)
    if letter:
        return record_email_fact(message.conversation, letter.connection, actor="AI",
                                 operation_id=operation_key("reply", message.pk))
    return record_public_reply(message)


def deliver_saved(source_id, context):
    with tenant_atomic(context):
        organization = lock_organization(context.organization_id)
        message = Message.objects.filter(
            ai_reply_to_id=source_id, organization_id=context.organization_id,
        ).first()
        if message is None or message.ai_delivery.get("sent") or message.ai_delivery.get("cancelled") or not message.text:
            return
        route = message.ai_delivery
        connection = Integration.objects.select_related("organization").filter(pk=route.get("connectionId"), organization_id=context.organization_id).first()
        if connection is None:
            return
        from chatballs.conversations.models import Conversation

        conversation = Conversation.objects.select_for_update(of=("self",)).select_related("channel__ai_agent", "connection").get(
            pk=message.conversation_id, organization_id=context.organization_id,
        )
        message = Message.objects.select_for_update().get(pk=message.pk, organization_id=context.organization_id)
        route = message.ai_delivery
        if route.get("sent") or route.get("cancelled"):
            return
        if route.get("actionRuns"):
            from chatballs.integrations.execution.ai_reply import allowed
            if not allowed(context, conversation.pk, route["actionRuns"]):
                return
        letter = getattr(message, "email_transport", None)
        # A continuation mailbox is a transport; autonomy belongs to the WEB source.
        source_connection = conversation.connection if letter else connection
        current_agent = getattr(conversation.channel, "ai_agent", None)
        # Keep both locks until the external transport accepts the message.
        # A mode transition cannot complete before an in-progress handoff.
        if (not connection.is_active or conversation.lifecycle != "OPEN" or conversation.control_mode == "HUMAN"
                or conversation.assigned_operator_id is not None
                or route.get("modeVersion", 1) != organization.operation_mode_version
                or route.get("controlVersion", 0) != conversation.ai_control_version
                or route.get("agentId", getattr(current_agent, "pk", None)) != getattr(current_agent, "pk", None)
                or route.get("agentVersion", configuration_version(current_agent)) != configuration_version(current_agent)
                or not autonomous_allowed(conversation.channel, organization=organization, connection=source_connection)):
            return
        outgoing = continuation_message(letter) if letter else None
        if outgoing is None and connection.provider == "EMAIL":
            outgoing = prepare_text(connection, target=route["chatId"], text=message.text, meta=route.get("mailMeta", {}))
            outgoing["Message-ID"] = route["messageId"]
        if outgoing is not None:
            accepted = deliver_message(connection, outgoing).state == "SMTP_ACCEPTED"
        else:
            accepted = transports.send_reply(connection, chat_id=route["chatId"], user_id=route["userId"], text=message.text)
        if not accepted:
            raise AiDeliveryFailed("AI reply transport rejected delivery")
        Message.objects.filter(pk=message.pk).update(ai_delivery={**route, "sent": True})
