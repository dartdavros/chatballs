from hub_platform.calls.errors import CallAccessDenied
from hub_platform.calls.models import CallSession
from hub_platform.conversations.models import Conversation
from hub_platform.identity.models import HumanUser
from hub_platform.identity.policy import require_capability


def ensure_conversation_call_access(*, user, conversation: Conversation) -> None:
    if not require_capability(user, "conversations.call", conversation):
        raise CallAccessDenied("Нет доступа к звонкам этого отдела")


def ensure_call_access(*, user, call_session: CallSession) -> None:
    ensure_conversation_call_access(user=user, conversation=call_session.conversation)


def staff_call_access_valid(*, user_id: int, call_session_id) -> bool:
    user = HumanUser.objects.filter(id=user_id).select_related(
        "employee_profile", "employee_profile__organization"
    ).first()
    call = CallSession.objects.select_related(
        "conversation", "conversation__channel"
    ).filter(id=call_session_id).first()
    if user is None or call is None:
        return False
    try:
        ensure_call_access(user=user, call_session=call)
    except CallAccessDenied:
        return False
    return True
