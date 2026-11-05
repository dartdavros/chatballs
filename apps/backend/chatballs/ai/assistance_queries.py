"""Protected assistance reads shared by HTTP and scenario actions."""

from chatballs.ai.assistance_access import reply_context
from chatballs.ai.assistance_expiry import expire_attempt
from chatballs.ai.assistance_payload import attempt_payload
from chatballs.ai.assistance_services import attempt_for
from chatballs.ai.models import ReplyAssistanceAttempt


def attempts(context, conversation_id):
    _, conversation = reply_context(context, conversation_id)
    rows = ReplyAssistanceAttempt.objects.filter(
        organization_id=context.organization_id, conversation=conversation,
    ).order_by("-created_at", "-id")[:20]
    return {"items": [attempt_payload(expire_attempt(row)) for row in rows]}


def detail(context, conversation_id, attempt_id):
    _, conversation = reply_context(context, conversation_id)
    attempt = attempt_for(context, conversation, attempt_id)
    return {"attempt": attempt_payload(expire_attempt(attempt))}
