from django.db import transaction

from chatballs.conversations.access import (
    require_conversation_action,
    require_independent_operation,
)
from chatballs.conversations.domain_operations import domain_operation
from chatballs.conversations.models import (
    ControlMode,
    Conversation,
    ExpectedResponder,
    LifecycleState,
)
from chatballs.conversations.queue import leave_queue
from chatballs.conversations.realtime import notify_conversation_changed
from chatballs.notifications.models import (
    Notification,
)
from chatballs.tenancy.context import TenantContext


@transaction.atomic
@domain_operation("CLOSED", guard=require_independent_operation)
def close_conversation(*, context: TenantContext, conversation_id: int) -> Conversation:
    conversation = Conversation.objects.select_for_update().get(
        id=conversation_id, organization=context.organization
    )
    from chatballs.conversations.services import _require_open
    require_independent_operation(context, conversation)
    _require_open(conversation)
    return _finish_conversation(conversation, LifecycleState.CLOSED)


@transaction.atomic
@domain_operation("QUEUE_EXITED", guard=require_independent_operation)
def mark_conversation_as_spam(
    *, context: TenantContext, conversation_id: int
) -> Conversation:
    conversation = Conversation.objects.select_for_update().get(
        id=conversation_id, organization=context.organization
    )
    from chatballs.conversations.services import _require_open
    require_independent_operation(context, conversation)
    _require_open(conversation)
    return _finish_conversation(conversation, LifecycleState.SPAM)


@transaction.atomic
def delete_conversation(*, context: TenantContext, conversation: Conversation) -> None:
    """Удалить диалог насовсем: переписку, вложения, звонки и оклики о нём.
    Раньше «удалить» означало архив: диалог пропадал из списков, но продолжал
    жить — в него приходили сообщения из канала, он поднимал уведомления и
    возвращался клиенту в виджете как ни в чём не бывало. Решение владельца
    2026-09-14: удалён — значит удалён. Права на это есть только у владельца и
    администратора (проверяет представление).
    Файлы удаляются явно: `FileField` при удалении строки оставляет их на
    диске, а «удалён» не должно означать «лежит в media».
    """
    # Assistance operations acquire the conversation lock before source rows.
    conversation = Conversation.objects.select_for_update().get(
        pk=conversation.pk, organization_id=context.organization_id,
    )
    require_conversation_action(context, conversation, "settings.manage")
    conversation_id = conversation.id
    organization_id = conversation.organization_id
    from chatballs.ai.external_agents.file_cleanup import release_conversation

    release_conversation(context, conversation_id)
    for message in conversation.messages.exclude(audio="", attachment=""):
        if message.audio:
            message.audio.delete(save=False)
        if message.attachment:
            message.attachment.delete(save=False)
    # Оклик ведёт в диалог, которого больше нет: и в списке уведомлений, и в
    # мессенджере сотрудника такая строка — тупик.
    Notification.objects.filter(
        organization_id=organization_id,
        source_type="Conversation",
        source_id=str(conversation_id),
    ).delete()
    # Звонки держат диалог внешним ключом PROTECT; история звонка без самого
    # диалога ничего не значит, поэтому уходит вместе с ним.
    from chatballs.calls.models import CallSession
    CallSession.objects.filter(conversation_id=conversation_id).delete()
    from chatballs.ai.assistance_cleanup import delete_conversation_assistance

    delete_conversation_assistance(conversation)
    conversation.delete()
    # Открытые рабочие места узнают об этом событием: у того, кто держал диалог
    # открытым, он должен закрыться, а не висеть мёртвой карточкой.
    notify_conversation_changed(conversation_id, organization_id=organization_id)


def _finish_conversation(conversation, lifecycle):
    conversation.lifecycle = lifecycle
    conversation.control_mode = ControlMode.PAUSED
    conversation.assigned_operator = None
    conversation.expected_responder = ExpectedResponder.NOBODY
    leave_queue(conversation)
    conversation.save(
        update_fields=[
            "lifecycle",
            "control_mode",
            "assigned_operator",
            "expected_responder",
            "waiting_since",
        ]
    )
    return conversation


@domain_operation("CLOSED", capability=None)
def _close_stale_locked(*, context, conversation):
    from chatballs.conversations.control_services import _require_open
    if context.actor_user is not None or context.membership is not None:
        raise Conversation.DoesNotExist
    _require_open(conversation)
    return _finish_conversation(conversation, LifecycleState.CLOSED)
