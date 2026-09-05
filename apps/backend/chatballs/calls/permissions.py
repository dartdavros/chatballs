from chatballs.calls.errors import CallAccessDenied
from chatballs.calls.models import CallSession
from chatballs.conversations.models import Conversation
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.policy import require_capability
from chatballs.tenancy.context import TenantContext


def ensure_conversation_call_access(*, user, conversation: Conversation) -> None:
    if not require_capability(user, "conversations.call", conversation):
        raise CallAccessDenied("Нет доступа к звонкам")
    from chatballs.conversations.selectors import conversation_is_visible

    if not conversation_is_visible(actor=user, conversation=conversation):
        raise CallAccessDenied("Диалог вне групп сотрудника")


def ensure_call_access(*, user, call_session: CallSession) -> None:
    ensure_conversation_call_access(user=user, conversation=call_session.conversation)


def staff_call_access_valid(*, context: TenantContext, call_session_id) -> bool:
    if context.membership is None or context.actor_user is None:
        return False
    call = CallSession.objects.select_related(
        "conversation", "conversation__channel"
    ).filter(id=call_session_id, organization=context.organization).first()
    if call is None:
        return False
    membership = OrganizationMembership.objects.select_related("user", "organization").filter(
        pk=context.membership_id,
        user=context.actor_user,
        organization=context.organization,
        blocked_at__isnull=True,
        user__is_active=True,
    ).first()
    if membership is None:
        return False
    try:
        ensure_call_access(user=membership, call_session=call)
    except CallAccessDenied:
        return False
    return True
