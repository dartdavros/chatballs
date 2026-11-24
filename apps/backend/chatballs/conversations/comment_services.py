"""Validate and append an internal comment without customer-reply effects."""

from functools import partial
from uuid import UUID

from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException, ValidationError

from chatballs.conversations.audience import ConversationAudience
from chatballs.conversations.comment_access import comment_conversation
from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.realtime import notify_comments_changed
from chatballs.i18n import t
from chatballs.identity.demo_seed.north_wind.support_artifacts import record_demo_support_operation
from chatballs.tenancy.database import tenant_atomic

MAX_COMMENT_LENGTH = 10_000


class CommentOperationConflict(APIException):
    status_code = 409
    default_code = "comment_operation_conflict"


def validate_comment(*, audience, text, operation_id):
    if audience != ConversationAudience.INTERNAL:
        raise ValidationError({"audience": t("comments.internal_required")})
    if not isinstance(text, str) or not text.strip():
        raise ValidationError({"text": t("comments.text_required")})
    if len(text) > MAX_COMMENT_LENGTH:
        raise ValidationError({"text": t("comments.text_too_long", limit=MAX_COMMENT_LENGTH)})
    if "\x00" in text or any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        raise ValidationError({"text": t("comments.text_invalid")})
    try:
        operation_id = UUID(str(operation_id))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValidationError({"operationId": t("comments.operation_invalid")}) from error
    return text.strip(), operation_id


@record_demo_support_operation
def create_comment(*, context, conversation_id, audience, text, operation_id):
    text, operation_id = validate_comment(audience=audience, text=text, operation_id=operation_id)
    with tenant_atomic(context):
        conversation = comment_conversation(
            context=context, conversation_id=conversation_id, capability="conversations.comment",
        )
        records = ConversationComment.objects.filter(organization_id=context.organization_id)
        existing = records.filter(operation_id=operation_id).first()
        if existing is None:
            try:
                # The unique organization/operation constraint arbitrates concurrent retries.
                with transaction.atomic():
                    comment = records.create(
                        organization_id=context.organization_id, conversation=conversation,
                        author_id=context.actor_user.pk, audience=audience,
                        text=text, operation_id=operation_id,
                    )
            except IntegrityError:
                existing = records.filter(operation_id=operation_id).first()
                if existing is None:
                    raise
            else:
                transaction.on_commit(partial(notify_comments_changed, conversation.pk))
                return comment, True
        if (existing.conversation_id, existing.author_id, existing.audience, existing.text) != (
            conversation.pk, context.actor_user.pk, audience, text,
        ):
            raise CommentOperationConflict(t("comments.operation_conflict"))
        return existing, False
