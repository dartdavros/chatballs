from django.db import transaction

from chatballs.conversations.access import require_independent_operation
from chatballs.conversations.domain_events import is_accepted
from chatballs.conversations.domain_operations import domain_operation
from chatballs.conversations.models import (
    ControlMode,
    Conversation,
    ExpectedResponder,
    LifecycleState,
    Message,
    MessageAuthor,
    SystemEvent,
)
from chatballs.conversations.queue import QUEUE_FIELDS, enter_queue, leave_queue
from chatballs.i18n import t
from chatballs.identity.operation_modes import (
    autonomous_allowed,
    lock_organization,
    serialize_autonomy,
)
from chatballs.identity.policy import ResourceScope, authorize
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class ClaimError(Exception):
    pass


def _require_open(conversation: Conversation) -> None:
    if conversation.lifecycle != LifecycleState.OPEN:
        raise ClaimError(t("conversations.closed"))


def operator_label(operator) -> str:
    return getattr(operator, "full_name", "") or operator.email


def claim_conversation(*, context: TenantContext, conversation_id: int, operation_id=None) -> Conversation:
    with tenant_atomic(context):
        conversation = Conversation.objects.select_for_update().get(
            id=conversation_id, organization=context.organization,
        )
        return claim_locked_conversation(
            context=context, conversation=conversation, operation_id=operation_id,
        )


@domain_operation("ACCEPTED", guard=require_independent_operation)
def claim_locked_conversation(*, context: TenantContext, conversation: Conversation) -> Conversation:
    """Claim an already locked conversation inside the caller's transaction."""
    operator = context.actor_user
    if operator is None or conversation.organization_id != context.organization_id:
        raise ClaimError(t("conversations.unavailable"))
    require_independent_operation(context, conversation)
    _require_open(conversation)
    # Владелец (OWNER) может перехватить диалог у любого оператора; прочие сотрудники
    # не могут забрать диалог, уже назначенный другому оператору.
    is_owner = authorize(context.membership, "ownership.transfer", ResourceScope(context.organization_id))
    if (
        not is_owner
        and conversation.control_mode == ControlMode.HUMAN
        and conversation.assigned_operator_id
        and conversation.assigned_operator_id != operator.id
    ):
        raise ClaimError(t("calls.conversation_taken"))
    if is_accepted(conversation) and conversation.assigned_operator_id == operator.pk:
        return conversation
    from chatballs.conversations.autonomous_execution import cancel_pending_replies

    cancel_pending_replies(conversation)
    was_queued = conversation.waiting_since is not None
    conversation.control_mode = ControlMode.HUMAN
    conversation.assigned_operator = operator
    conversation.expected_responder = ExpectedResponder.OPERATOR
    leave_queue(conversation)
    conversation.save(update_fields=["control_mode", "assigned_operator", "expected_responder", "waiting_since"])
    Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.SYSTEM,
        author_user=operator,
        system_event=SystemEvent.OPERATOR_TOOK,
        system_params={"operator": operator_label(operator), "fromQueue": was_queued},
        text=f"Оператор {operator_label(operator)} перехватил диалог",
    )
    return conversation


@transaction.atomic
@serialize_autonomy
@domain_operation("QUEUE_EXITED", guard=require_independent_operation)
def release_to_ai(*, context: TenantContext, conversation_id: int) -> Conversation:
    organization = lock_organization(context.organization_id)
    if organization.operation_mode == "OPERATORS_ONLY":
        raise ClaimError(t("conversations.operators_only"))
    conversation = Conversation.objects.select_for_update().get(
        id=conversation_id, organization=context.organization
    )
    require_independent_operation(context, conversation)
    _require_open(conversation)
    if not autonomous_allowed(conversation.channel, organization=organization, connection=conversation.connection):
        raise ClaimError(t("channels.no_active_agent"))
    conversation.control_mode = ControlMode.AI
    conversation.assigned_operator = None
    conversation.expected_responder = ExpectedResponder.AI
    leave_queue(conversation)
    conversation.save(update_fields=["control_mode", "assigned_operator", "expected_responder", "waiting_since"])
    Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.SYSTEM,
        system_event=SystemEvent.RETURNED_TO_AI,
        system_params={"externalExecution": getattr(getattr(conversation.channel, "ai_agent", None), "execution_mode", "builtin") == "external"},
        text="",
    )
    return conversation


@transaction.atomic
@domain_operation("QUEUE_ENTERED", guard=require_independent_operation)
def return_to_queue(*, context: TenantContext, conversation_id: int) -> Conversation:
    # Оператор возвращает диалог в общую очередь (ADR-CHATBALLS-0003): снят с себя, ждёт оператора.
    conversation = Conversation.objects.select_for_update().get(
        id=conversation_id, organization=context.organization
    )
    require_independent_operation(context, conversation)
    _require_open(conversation)
    enter_queue(conversation)
    conversation.assigned_operator = None
    conversation.save(update_fields=[*QUEUE_FIELDS, "assigned_operator"])
    Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.SYSTEM,
        system_event=SystemEvent.RETURNED_TO_QUEUE,
        text="Диалог возвращён в очередь",
    )
    return conversation
