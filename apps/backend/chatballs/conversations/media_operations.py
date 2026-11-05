"""Original media retry/transaction boundary, independent of HTTP dispatch."""

from functools import wraps
from uuid import UUID, uuid4

from rest_framework.exceptions import ValidationError

from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.domain_events import record_public_reply
from chatballs.conversations.models import Conversation, Message
from chatballs.conversations.operator_reply import reply_conversation
from chatballs.conversations.reply_access import lock_for_reply, require_human_reply
from chatballs.conversations.reply_problems import ReplyProblem, problem
from chatballs.conversations.services import ClaimError
from chatballs.i18n import t
from chatballs.tenancy.database import tenant_atomic


def media_operation(kind):
    def decorate(function):
        @wraps(function)
        def execute(*, context, conversation_id, operation_id=None, request=None, **values):
            try:
                operation_id = UUID(str(operation_id)) if operation_id else uuid4()
            except (ValueError, TypeError, AttributeError) as error:
                raise ValidationError(t("transfers.operation_invalid")) from error
            with tenant_atomic(context):
                try:
                    reply_conversation(context, conversation_id)
                    conversation = lock_for_reply(context=context, conversation_id=conversation_id)
                    prior = ConversationEvent.objects.filter(organization_id=context.organization_id,
                        operation_id=operation_id).first()
                    if prior:
                        require_human_reply(context=context, conversation=conversation)
                        if (prior.conversation_id != conversation_id
                                or prior.initiated_by_id != context.actor_user.pk
                                or prior.event_type != "PUBLIC_REPLY"):
                            raise ValidationError(t("transfers.operation_invalid"))
                        message = Message.objects.get(conversation_id=conversation_id,
                            external_id=f"operation:{operation_id}")
                        if message.kind != kind:
                            raise ValidationError(t("transfers.operation_invalid"))
                        return message
                    outcome = function(context=context, conversation=conversation,
                        operation_id=operation_id, request=request, **values)
                    if isinstance(outcome, ReplyProblem):
                        # Source HTTP failures commit a preceding successful claim,
                        # just as the original Response-returning media operation.
                        return outcome
                    outcome.external_id = f"operation:{operation_id}"
                    outcome.save(update_fields=["external_id"])
                    record_public_reply(outcome, operation_id=operation_id)
                    return outcome
                except Conversation.DoesNotExist:
                    return problem("conversations.not_found", 404)
                except ClaimError as error:
                    return ReplyProblem({"detail": str(error)}, 409)
        return execute
    return decorate
