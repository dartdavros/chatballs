from chatballs.conversations.models import (
    ConnectionIdentity,
    Conversation,
    Message,
    MessageAuthor,
)
from chatballs.integrations.models import IntegrationProvider


def _history_item(conversation: Conversation) -> dict[str, object]:
    last = _last_message(conversation)
    # Тема карточки истории (кадр F) — первая реплика клиента; кто вёл — ответственный или AI.
    first = (
        conversation.messages.filter(author_type=MessageAuthor.CONTACT)
        .order_by("created_at", "id")
        .values_list("text", flat=True)
        .first()
    )
    operator = conversation.assigned_operator
    return {
        "id": conversation.id,
        "channelName": conversation.channel.name,
        "provider": conversation.connection.provider if conversation.connection_id else None,
        "lifecycle": conversation.lifecycle,
        "createdAt": conversation.created_at.isoformat(),
        "lastActivityAt": conversation.last_activity_at.isoformat(),
        "topic": (first or "").replace("\n", " ")[:80],
        "handledBy": (operator.full_name or operator.email) if operator else None,
        "preview": last.text.replace("\n", " ")[:80] if last else "",
    }


def _connection_identity(conversation: Conversation) -> ConnectionIdentity | None:
    # Username и подпись гостя живут на identity подключения (у контакта их
    # может быть несколько). Только в detail-режиме — в списках это лишний
    # запрос на каждый диалог.
    if not conversation.connection_id:
        return None
    return ConnectionIdentity.objects.filter(
        connection_id=conversation.connection_id, contact_id=conversation.contact_id
    ).first()


def _contact_is_guest(contact, identity: ConnectionIdentity | None) -> bool:
    # Гость виджета получает имя «Гость · <код сессии>» на языке организации;
    # та же подпись записана в display_name его identity. Пока имя не сменили,
    # настоящего имени у контакта нет — подставлять его в ответ нельзя.
    if not contact.name:
        return True
    return bool(
        identity
        and identity.display_name == contact.name
        and identity.external_user_id[:6] in contact.name
    )


def _contact_email(conversation: Conversation) -> str:
    if conversation.contact.email:
        return conversation.contact.email
    if (
        conversation.connection_id
        and conversation.connection.provider == IntegrationProvider.EMAIL
    ):
        return conversation.external_chat_id
    return ""


def _conversation_history(conversation: Conversation, viewer_id=None) -> list[Conversation]:
    # Цепочка прошлых обращений того же контакта (ADR-CHATBALLS-0002).
    from chatballs.conversations.selectors import visible_conversations_for
    from chatballs.identity.models import OrganizationMembership
    from chatballs.tenancy.context import TenantContext

    actor = OrganizationMembership.objects.filter(
        organization_id=conversation.organization_id, user_id=viewer_id,
    ).first() if viewer_id else None
    if actor is None:
        return []
    qs = visible_conversations_for(TenantContext.for_membership(actor)).filter(contact_id=conversation.contact_id)
    return list(
        qs.exclude(id=conversation.id)
        .select_related("channel", "connection", "assigned_operator")
        .order_by("-last_activity_at")[:10]
    )

def _last_message(conversation: Conversation) -> Message | None:
    # Превью строки списка — последняя реплика клиента/AI/сотрудника; системные
    # события («AI передал диалог») в превью не показываются (дизайн-базлайн v2, B).
    return (
        conversation.messages.exclude(author_type=MessageAuthor.SYSTEM)
        .select_related("author_user", "email_transport", "externalagentdeliveryitem__delivery__request")
        .order_by("-created_at", "-id")
        .first()
    )
