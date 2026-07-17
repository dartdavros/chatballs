"""Poll/send сообщений support-диалога для виджета (SPEC-HUB-0010 §7).

В отличие от sales webchat (ingest_inbound), support-путь НЕ создаёт Contact и НЕ
ходит в мессенджер (transports.send_reply): ответ оператора/AI виджет забирает
polling'ом. AI-путь (run_channel_turn + handoff + system) переиспользуется.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from hub_platform.ai.credits import ManagedAiQuotaExceeded
from hub_platform.ai.limits import LimitExceeded
from hub_platform.ai.provider.base import ProviderError
from hub_platform.ai.runtime import HANDOFF_TOKEN
from hub_platform.channels.runtime import run_channel_turn
from hub_platform.conversations.models import (
    ControlMode,
    Conversation,
    ExpectedResponder,
    Message,
    MessageAuthor,
)
from hub_platform.notifications.models import NotificationAudience, NotificationType
from hub_platform.notifications.services import notify, notify_management
from hub_platform.subscriptions.errors import EntitlementRequired
from hub_platform.tenancy.context import TenantContext

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
    return [{"role": _ROLE.get(m.author_type, "user"), "content": m.text} for m in prior if m.text]


def support_messages_since(conversation: Conversation, since: int) -> dict:
    items = conversation.messages.filter(id__gt=since).order_by("created_at")
    return {
        "state": _STATE.get(conversation.control_mode, "ai"),
        "lifecycle": conversation.lifecycle,
        "messages": [
            {
                "id": m.id,
                "author": _AUTHOR.get(m.author_type, "ai"),
                "text": m.text,
                "createdAt": m.created_at.isoformat(),
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
    snapshot = conversation.support_identity_snapshot
    client_label = (snapshot.display_name if snapshot else "") or "Клиент"
    conversation.last_activity_at = timezone.now()
    conversation.save(update_fields=["last_activity_at"])

    # AI отвечает только когда диалог ведёт AI (ADR-HUB-0003).
    if conversation.control_mode != ControlMode.AI:
        return

    try:
        result = run_channel_turn(
            channel=conversation.channel, message=text, history=_history(conversation)
        )
    except (
        ProviderError,
        ManagedAiQuotaExceeded,
        LimitExceeded,
        EntitlementRequired,
    ) as error:
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
            department=conversation.channel.department,
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
            department=conversation.channel.department,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title=f"AI передал диалог · {client_label}",
            body=text[:120],
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"handoff:{conversation.id}",
        )
