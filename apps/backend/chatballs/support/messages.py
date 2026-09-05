"""Poll/send сообщений support-диалога для виджета (SPEC-HUB-0010 §7).

В отличие от sales webchat (ingest_inbound), support-путь НЕ создаёт Contact и НЕ
ходит в мессенджер (transports.send_reply): ответ оператора/AI виджет забирает
polling'ом. AI-путь (run_channel_turn + handoff + system) переиспользуется.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from chatballs.ai.limits import LimitExceeded
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.runtime import HANDOFF_TOKEN
from chatballs.channels.runtime import run_channel_turn
from chatballs.conversations.models import (
    ControlMode,
    Conversation,
    ExpectedResponder,
    Message,
    MessageAuthor,
    MessageKind,
)
from chatballs.notifications.models import NotificationAudience, NotificationType
from chatballs.notifications.services import notify, notify_management
from chatballs.tenancy.context import TenantContext

logger = logging.getLogger(__name__)

_HISTORY_LIMIT = 20
_ROLE = {
    MessageAuthor.CONTACT: "user",
    MessageAuthor.AI: "assistant",
    MessageAuthor.OPERATOR: "assistant",
    MessageAuthor.SYSTEM: "system",
}
_STATE = {
    ControlMode.AI: "ai",
    ControlMode.HUMAN: "operator",
    ControlMode.PAUSED: "waiting",
}
_AUTHOR = {
    MessageAuthor.CONTACT: "client",
    MessageAuthor.AI: "ai",
    MessageAuthor.OPERATOR: "operator",
    MessageAuthor.SYSTEM: "system",
}


def _history(conversation: Conversation) -> list[dict]:
    messages = list(conversation.messages.order_by("created_at"))
    prior = messages[:-1][-_HISTORY_LIMIT:]
    # Голосовые попадают в контекст стенограммой.
    return [{"role": _ROLE.get(m.author_type, "user"), "content": m.text or m.transcript} for m in prior if m.text or m.transcript]


def support_messages_since(conversation: Conversation, since: int) -> dict:
    items = conversation.messages.filter(id__gt=since).order_by("created_at")
    return {
        "state": _STATE.get(conversation.control_mode, "ai"),
        "lifecycle": conversation.lifecycle,
        "messages": [
            {
                "id": m.id,
                "author": _AUTHOR.get(m.author_type, "ai"),
                "kind": m.kind,
                "text": m.text,
                "createdAt": m.created_at.isoformat(),
                "durationSeconds": m.duration_seconds,
                "hasAudio": bool(m.audio),
                **(
                    {
                        "attachment": {
                            "name": m.attachment_name,
                            "contentType": m.attachment_content_type,
                            "size": m.attachment_size,
                            "available": bool(m.attachment),
                        }
                    }
                    if m.kind == MessageKind.FILE
                    else {}
                ),
            }
            for m in items
        ],
    }


@transaction.atomic
def post_support_message(
    *, context: TenantContext, conversation: Conversation, text: str
) -> None:
    """Сохраняет сообщение клиента и запускает AI-ответ (если диалог ведёт AI).

    ADR-HUB-0003: AI-first; handoff AI→operator. Без Contact/ConnectionIdentity и
    без transports.send_reply (ответ идёт через polling, не через messenger API).
    """
    if conversation.organization_id != context.organization_id:
        raise ValueError("Support conversation is outside tenant context")
    Message.objects.create(conversation=conversation, author_type=MessageAuthor.CONTACT, text=text)
    conversation.last_activity_at = timezone.now()
    conversation.save(update_fields=["last_activity_at"])
    _run_support_ai(context=context, conversation=conversation, text=text)


def _client_label(conversation: Conversation) -> str:
    snapshot = conversation.support_identity_snapshot
    return (snapshot.display_name if snapshot else "") or "Клиент"


def _hand_to_operator(*, context: TenantContext, conversation: Conversation, reason: str) -> None:
    """Диалог уходит оператору без имитации сбоя AI (голосовое без стенограммы, файл)."""
    if conversation.control_mode != ControlMode.AI:
        return
    conversation.control_mode = ControlMode.PAUSED
    conversation.expected_responder = ExpectedResponder.OPERATOR
    conversation.save(update_fields=["control_mode", "expected_responder"])
    notify(
        context=context,
        type=NotificationType.DIALOG_WAITING,
        audience=NotificationAudience.OPERATORS,
        title=f"Нужен оператор · {_client_label(conversation)}",
        body=reason,
        target_id=conversation.id,
        source_type="Conversation",
        source_id=conversation.id,
        dedup_key=f"media:{conversation.id}",
    )


@transaction.atomic
def post_support_voice(*, context: TenantContext, conversation: Conversation, content: bytes, content_type: str, duration: int) -> Message:
    """Голосовое из портала поддержки: сохраняем, AI отвечает текстом по
    стенограмме; без расшифровки — диалог оператору."""
    from django.core.files.base import ContentFile

    from chatballs.conversations.ingest import transcribe_voice_message

    if conversation.organization_id != context.organization_id:
        raise ValueError("Support conversation is outside tenant context")
    message = Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.CONTACT,
        kind=MessageKind.VOICE,
        audio_content_type=content_type,
        duration_seconds=duration,
    )
    suffix = "ogg" if "ogg" in content_type else content_type.rsplit("/", 1)[-1]
    message.audio.save(f"voice.{suffix}", ContentFile(content), save=False)
    message.save(update_fields=["audio"])
    conversation.last_activity_at = timezone.now()
    conversation.save(update_fields=["last_activity_at"])
    if conversation.control_mode != ControlMode.AI:
        return message
    transcript = transcribe_voice_message(conversation.channel, message)
    if transcript:
        _run_support_ai(context=context, conversation=conversation, text=transcript)
    else:
        _hand_to_operator(context=context, conversation=conversation, reason="Голосовое без расшифровки")
    return message


@transaction.atomic
def post_support_file(*, context: TenantContext, conversation: Conversation, content: bytes, filename: str, content_type: str, caption: str = "") -> Message:
    """Файл из портала поддержки: подпись — обычное сообщение (с ответом AI),
    сам файл — отдельная реплика; файл без подписи уводит диалог оператору."""
    from django.core.files.base import ContentFile

    if conversation.organization_id != context.organization_id:
        raise ValueError("Support conversation is outside tenant context")
    if caption:
        Message.objects.create(conversation=conversation, author_type=MessageAuthor.CONTACT, text=caption)
    message = Message.objects.create(
        conversation=conversation,
        author_type=MessageAuthor.CONTACT,
        kind=MessageKind.FILE,
        attachment_name=filename,
        attachment_content_type=content_type,
        attachment_size=len(content),
    )
    message.attachment.save(filename, ContentFile(content), save=False)
    message.save(update_fields=["attachment"])
    conversation.last_activity_at = timezone.now()
    conversation.save(update_fields=["last_activity_at"])
    if caption:
        _run_support_ai(context=context, conversation=conversation, text=caption)
    else:
        _hand_to_operator(context=context, conversation=conversation, reason=f"Файл: {filename}")
    return message


def _run_support_ai(*, context: TenantContext, conversation: Conversation, text: str) -> None:
    client_label = _client_label(conversation)
    # AI отвечает только когда диалог ведёт AI (ADR-HUB-0003).
    if conversation.control_mode != ControlMode.AI:
        return

    try:
        result = run_channel_turn(
            channel=conversation.channel, message=text, history=_history(conversation)
        )
    except (ProviderError, LimitExceeded) as error:
        logger.warning("AI turn failed for support conversation %s: %s", conversation.id, error)
        conversation.control_mode = ControlMode.PAUSED
        conversation.expected_responder = ExpectedResponder.OPERATOR
        conversation.last_activity_at = timezone.now()
        conversation.save(
            update_fields=["control_mode", "expected_responder", "last_activity_at"]
        )
        Message.objects.create(
            conversation=conversation,
            author_type=MessageAuthor.SYSTEM,
            text="AI недоступен — диалог передан оператору",
        )
        fallback = (
            "Извините, прямо сейчас не получается ответить. Я передал ваш вопрос"
            " специалисту — он скоро подключится."
        )
        Message.objects.create(
            conversation=conversation, author_type=MessageAuthor.AI, text=fallback
        )
        notify(
            context=context,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title=f"Нужен оператор · {client_label}",
            body="AI временно недоступен, диалог ждёт ответа",
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"aifail:{conversation.id}",
        )
        notify_management(
            context=context,
            type=NotificationType.INTEGRATION_ERROR,
            title=f"Ошибка AI · {conversation.channel.name}",
            body="AI временно недоступен, диалог передан оператору",
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"aierror:{conversation.id}",
        )
        return

    reply = result.text
    handoff = HANDOFF_TOKEN in reply
    if handoff:
        reply = reply.replace(HANDOFF_TOKEN, "").strip()

    Message.objects.create(conversation=conversation, author_type=MessageAuthor.AI, text=reply)
    conversation.last_activity_at = timezone.now()
    if handoff:
        conversation.control_mode = ControlMode.PAUSED
        conversation.expected_responder = ExpectedResponder.OPERATOR
    else:
        conversation.expected_responder = ExpectedResponder.CUSTOMER
    conversation.save(update_fields=["control_mode", "last_activity_at", "expected_responder"])

    if handoff:
        Message.objects.create(
            conversation=conversation,
            author_type=MessageAuthor.SYSTEM,
            text="AI передал диалог оператору",
        )
        notify(
            context=context,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title=f"AI передал диалог · {client_label}",
            body=text[:120],
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"handoff:{conversation.id}",
        )
