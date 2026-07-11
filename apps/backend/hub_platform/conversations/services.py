from django.db import transaction
from django.utils import timezone

from hub_platform.conversations import transports
from hub_platform.conversations.models import (
    ConnectionIdentity,
    Conversation,
    ControlMode,
    ExpectedResponder,
    LifecycleState,
    Message,
    MessageAuthor,
    MessageKind,
)
from hub_platform.integrations.models import IntegrationProvider

CONTACT_REQUEST_TEXT = "Поделитесь, пожалуйста, контактом — нажмите кнопку ниже."
CONTACT_REQUEST_TEXT_WEB = "Поделитесь, пожалуйста, номером телефона."


class ClaimError(Exception):
    pass


def _operator_label(operator) -> str:
    return getattr(operator, "full_name", "") or operator.email


@transaction.atomic
def claim_conversation(*, conversation_id: int, operator) -> Conversation:
    # Атомарный перехват у AI (ADR-HUB-0003): только один оператор забирает диалог.
    conversation = Conversation.objects.select_for_update().get(id=conversation_id)
    return claim_locked_conversation(conversation=conversation, operator=operator)


def claim_locked_conversation(*, conversation: Conversation, operator) -> Conversation:
    """Claim an already locked conversation inside the caller's transaction."""
    if (
        conversation.control_mode == ControlMode.HUMAN
        and conversation.assigned_operator_id
        and conversation.assigned_operator_id != operator.id
    ):
        raise ClaimError("Диалог уже ведёт другой оператор")
    conversation.control_mode = ControlMode.HUMAN
    conversation.assigned_operator = operator
    conversation.expected_responder = ExpectedResponder.OPERATOR
    conversation.save(update_fields=["control_mode", "assigned_operator", "expected_responder"])
    Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.SYSTEM,
        text=f"Оператор {_operator_label(operator)} перехватил диалог",
    )
    return conversation


@transaction.atomic
def release_to_ai(*, conversation_id: int) -> Conversation:
    conversation = Conversation.objects.select_for_update().get(id=conversation_id)
    conversation.control_mode = ControlMode.AI
    conversation.assigned_operator = None
    conversation.expected_responder = ExpectedResponder.AI
    conversation.save(update_fields=["control_mode", "assigned_operator", "expected_responder"])
    Message.objects.create(conversation=conversation, author_type=MessageAuthor.SYSTEM, text="Диалог возвращён AI")
    return conversation


@transaction.atomic
def return_to_queue(*, conversation_id: int) -> Conversation:
    # Оператор возвращает диалог в общую очередь (ADR-HUB-0003): снят с себя, ждёт оператора.
    conversation = Conversation.objects.select_for_update().get(id=conversation_id)
    conversation.control_mode = ControlMode.PAUSED
    conversation.assigned_operator = None
    conversation.expected_responder = ExpectedResponder.OPERATOR
    conversation.save(update_fields=["control_mode", "assigned_operator", "expected_responder"])
    Message.objects.create(conversation=conversation, author_type=MessageAuthor.SYSTEM, text="Диалог возвращён в очередь")
    return conversation


def post_operator_message(*, conversation: Conversation, operator, text: str) -> Message:
    message = Message.objects.create(
        conversation=conversation, author_type=MessageAuthor.OPERATOR, author_user=operator, text=text
    )
    conversation.last_activity_at = timezone.now()
    conversation.expected_responder = ExpectedResponder.CUSTOMER
    conversation.save(update_fields=["last_activity_at", "expected_responder"])
    # Отправляем в тот же мессенджер, откуда пришёл клиент.
    if conversation.connection_id:
        identity = ConnectionIdentity.objects.filter(
            connection=conversation.connection, contact=conversation.contact
        ).first()
        transports.send_reply(
            conversation.connection,
            chat_id=conversation.external_chat_id,
            user_id=identity.external_user_id if identity else "",
            text=text,
        )
    return message


def request_contact(*, conversation: Conversation, operator) -> Message:
    """Запрос контакта у клиента: TG/MAX — сообщение с кнопкой «Поделиться
    контактом», Web — виджет рисует форму телефона по kind=contact_request."""
    is_web = conversation.connection_id and conversation.connection.provider == IntegrationProvider.WEB
    text = CONTACT_REQUEST_TEXT_WEB if is_web else CONTACT_REQUEST_TEXT
    message = Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.OPERATOR,
        author_user=operator,
        kind=MessageKind.CONTACT_REQUEST,
        text=text,
    )
    conversation.last_activity_at = timezone.now()
    conversation.expected_responder = ExpectedResponder.CUSTOMER
    conversation.save(update_fields=["last_activity_at", "expected_responder"])
    if conversation.connection_id:
        identity = ConnectionIdentity.objects.filter(
            connection=conversation.connection, contact=conversation.contact
        ).first()
        transports.send_contact_request(
            conversation.connection,
            chat_id=conversation.external_chat_id,
            user_id=identity.external_user_id if identity else "",
            text=text,
        )
    return message


@transaction.atomic
def close_conversation(*, conversation_id: int) -> Conversation:
    conversation = Conversation.objects.select_for_update().get(id=conversation_id)
    conversation.lifecycle = LifecycleState.CLOSED
    conversation.expected_responder = ExpectedResponder.NOBODY
    conversation.save(update_fields=["lifecycle", "expected_responder"])
    return conversation
