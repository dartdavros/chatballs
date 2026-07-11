from hub_platform.calls.errors import CallAccessDenied
from hub_platform.calls.models import CallSession
from hub_platform.conversations.models import Conversation
from hub_platform.identity.models import EmployeeRole


def ensure_conversation_call_access(*, user, conversation: Conversation) -> None:
    profile = getattr(user, "employee_profile", None)
    if (
        not user.is_authenticated
        or not user.is_active
        or profile is None
        or profile.is_blocked
        or profile.organization_id != conversation.organization_id
        or profile.role not in {EmployeeRole.OWNER, EmployeeRole.OPERATOR}
    ):
        raise CallAccessDenied("Нет доступа к звонкам этого диалога")
    if profile.role == EmployeeRole.OPERATOR and (
        profile.department_id is None or profile.department_id != conversation.channel.department_id
    ):
        raise CallAccessDenied("Нет доступа к звонкам этого отдела")


def ensure_call_access(*, user, call_session: CallSession) -> None:
    ensure_conversation_call_access(user=user, conversation=call_session.conversation)
