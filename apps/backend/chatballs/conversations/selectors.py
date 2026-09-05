from django.db.models import F, Max, Q, QuerySet

from chatballs.conversations.models import Conversation
from chatballs.identity.policy import conversation_visibility
from chatballs.tenancy.context import TenantContext


def conversations_for_context(context: TenantContext) -> QuerySet[Conversation]:
    return (
        Conversation.objects.filter(organization_id=context.organization_id)
        .select_related(
            "channel",
            "channel__product",
            "contact",
            "connection",
            "assigned_operator",
            "support_identity_snapshot",
            "group",
        )
        .prefetch_related("labels")
        # Инбокс сортируется по времени последнего сообщения (а не по служебной
        # активности вроде claim/takeover); fallback — last_activity_at для
        # диалогов без сообщений.
        .annotate(_last_message_at=Max("messages__created_at"))
        .order_by(F("_last_message_at").desc(nulls_last=True), "-last_activity_at")
    )


def apply_conversation_visibility(
    queryset: QuerySet[Conversation], context: TenantContext
) -> QuerySet[Conversation]:
    """Видимость диалогов (ADR-HUB-0043 §4): OWNER/ADMIN — все; сотрудник —
    диалоги своих групп + без группы + где он ответственный."""
    scope = conversation_visibility(context.membership)
    if scope is None:
        return queryset
    if scope.get("none"):
        return queryset.none()
    return queryset.filter(
        Q(group__isnull=True)
        | Q(group_id__in=scope["group_ids"])
        | Q(assigned_operator_id=scope["user_id"])
    )


def conversation_is_visible(*, actor, conversation: Conversation) -> bool:
    """Точечная проверка той же видимости для уже загруженного диалога."""
    scope = conversation_visibility(actor)
    if scope is None:
        return True
    if scope.get("none"):
        return False
    return (
        conversation.group_id is None
        or conversation.group_id in scope["group_ids"]
        or conversation.assigned_operator_id == scope["user_id"]
    )


def visible_conversations_for(context: TenantContext) -> QuerySet[Conversation]:
    return apply_conversation_visibility(conversations_for_context(context), context)


def conversation_for_context(*, context: TenantContext, conversation_id: int) -> Conversation:
    return visible_conversations_for(context).get(id=conversation_id)
