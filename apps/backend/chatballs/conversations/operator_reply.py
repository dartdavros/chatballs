"""Product text/contact commands shared by HTTP and scenario actions."""

from rest_framework import serializers

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.models import Conversation, LifecycleState
from chatballs.conversations.reply_audit import audit_reply
from chatballs.conversations.reply_claim_service import claim_reply
from chatballs.conversations.reply_problems import ReplyProblem, problem
from chatballs.conversations.selectors import conversation_for_context
from chatballs.conversations.services import ClaimError, post_operator_message, request_contact
from chatballs.conversations.template_send_guard import (
    UnfilledTemplateVariables,
    require_filled_text,
)


def reply_conversation(context, conversation_id):
    conversation = conversation_for_context(context=context, conversation_id=conversation_id)
    require_conversation_action(context, conversation, "conversations.operate")
    return conversation


def send_text_reply(*, context, conversation_id, text, operation_id=None,
                    suggestion_id=None, suggestion_key=None, request=None):
    try:
        conversation = reply_conversation(context, conversation_id)
        text = str(text).strip()
        if not text:
            return problem("ai.empty_message")
        if conversation.lifecycle != LifecycleState.OPEN:
            return problem("conversations.closed", 409)
        try:
            require_filled_text(text)
        except UnfilledTemplateVariables as error:
            return ReplyProblem(error.payload(), 400)
        if suggestion_id is not None:
            from chatballs.ai.assistance_send import send_suggestion
            return send_suggestion(context=context, conversation_id=conversation_id,
                suggestion_id=serializers.UUIDField().run_validation(suggestion_id),
                key=suggestion_key, text=text)
        conversation = claim_reply(context=context, conversation_id=conversation_id,
            operation_id=operation_id, request=request)
        return post_operator_message(context=context, conversation=conversation,
            text=text, operation_id=operation_id)
    except Conversation.DoesNotExist:
        return problem("conversations.not_found", 404)
    except ClaimError as error:
        return ReplyProblem({"detail": str(error)}, 409)


def send_contact_request(*, context, conversation_id, operation_id=None, request=None):
    try:
        conversation = reply_conversation(context, conversation_id)
        if not conversation.contact_id or not conversation.connection_id:
            return problem("conversations.no_channel_for_contact", 409)
        if conversation.lifecycle != LifecycleState.OPEN:
            return problem("conversations.closed", 409)
        if conversation.contact.phone:
            return problem("conversations.contact_already_received", 409)
        message = request_contact(context=context, conversation=conversation, operation_id=operation_id)
        audit_reply(context, "contact_requested", conversation, request=request)
        return message
    except Conversation.DoesNotExist:
        return problem("conversations.not_found", 404)
    except ClaimError as error:
        return ReplyProblem({"detail": str(error)}, 409)
