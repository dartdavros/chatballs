from django.db.models import QuerySet

from hub_platform.conversations.models import Conversation


def conversations_for_organization(organization_id: int) -> QuerySet[Conversation]:
    return (
        Conversation.objects.filter(organization_id=organization_id)
        .select_related("channel", "channel__product", "contact", "connection", "assigned_operator")
        .order_by("-last_activity_at")
    )


def conversation_for_organization(*, organization_id: int, conversation_id: int) -> Conversation:
    return conversations_for_organization(organization_id).get(id=conversation_id)
