from django.db.models import F, Max, QuerySet

from hub_platform.conversations.models import Conversation


def conversations_for_organization(organization_id: int) -> QuerySet[Conversation]:
    return (
        Conversation.objects.filter(organization_id=organization_id)
        .select_related(
            "channel",
            "channel__product",
            "contact",
            "connection",
            "assigned_operator",
            "support_identity_snapshot",
        )
        # Инбокс сортируется по времени последнего сообщения (а не по служебной
        # активности вроде claim/takeover); fallback — last_activity_at для
        # диалогов без сообщений.
        .annotate(_last_message_at=Max("messages__created_at"))
        .order_by(F("_last_message_at").desc(nulls_last=True), "-last_activity_at")
    )


def conversation_for_organization(*, organization_id: int, conversation_id: int) -> Conversation:
    return conversations_for_organization(organization_id).get(id=conversation_id)
