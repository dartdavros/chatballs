"""Inbound ingest for messenger connections (M2a).

One inbound message -> contact/conversation/message -> AI turn (if the dialog is
AI-controlled) -> outbound reply. Idempotent via the events InboxEvent.
"""

from __future__ import annotations

import hashlib
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from hub_platform.ai.provider.base import ProviderError
from hub_platform.channels.runtime import run_channel_turn
from hub_platform.conversations.models import (
    ConnectionIdentity,
    Contact,
    Conversation,
    ControlMode,
    ExpectedResponder,
    LifecycleState,
    Message,
    MessageAuthor,
)
from hub_platform.conversations import transports
from hub_platform.conversations.transports.base import InboundMessage
from hub_platform.events.models import InboxEvent
from hub_platform.notifications.models import NotificationAudience, NotificationType
from hub_platform.notifications.services import notify

logger = logging.getLogger(__name__)

_HISTORY_LIMIT = 20
_ROLE = {
    MessageAuthor.CONTACT: "user",
    MessageAuthor.AI: "assistant",
    MessageAuthor.OPERATOR: "assistant",
    MessageAuthor.SYSTEM: "system",
}


def _already_processed(source: str, external_id: str, text: str) -> bool:
    payload_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    try:
        InboxEvent.objects.create(source=source, external_event_id=external_id, payload_hash=payload_hash)
        return False
    except IntegrityError:
        return True


def _history(conversation: Conversation) -> list[dict]:
    messages = list(conversation.messages.order_by("created_at"))
    prior = messages[:-1][-_HISTORY_LIMIT:]  # без только что сохранённого входящего
    return [{"role": _ROLE.get(m.author_type, "user"), "content": m.text} for m in prior if m.text]


def ingest_inbound(integration, inbound: InboundMessage) -> None:
    channel = integration.channel
    if channel is None:
        logger.warning("Integration %s has no channel — inbound dropped", integration.id)
        return
    source = f"{integration.provider.lower()}:{integration.id}"
    if _already_processed(source, inbound.external_id, inbound.text):
        return

    with transaction.atomic():
        identity = (
            ConnectionIdentity.objects.select_related("contact")
            .filter(connection=integration, external_user_id=inbound.user_id)
            .first()
        )
        if identity is None:
            contact = Contact.objects.create(organization=channel.organization, name=inbound.display_name)
            identity = ConnectionIdentity.objects.create(
                contact=contact, connection=integration, external_user_id=inbound.user_id, display_name=inbound.display_name
            )
        contact = identity.contact

        conversation = (
            Conversation.objects.filter(channel=channel, contact=contact, lifecycle=LifecycleState.OPEN)
            .order_by("-last_activity_at")
            .first()
        )
        is_new = conversation is None
        if conversation is None:
            conversation = Conversation.objects.create(
                organization=channel.organization,
                channel=channel,
                connection=integration,
                contact=contact,
                external_chat_id=inbound.chat_id,
                control_mode=ControlMode.AI,
                expected_responder=ExpectedResponder.AI,
            )
        elif inbound.chat_id and not conversation.external_chat_id:
            conversation.external_chat_id = inbound.chat_id

        Message.objects.create(
            conversation=conversation, author_type=MessageAuthor.CONTACT, text=inbound.text, external_id=inbound.external_id
        )
        conversation.last_activity_at = timezone.now()
        conversation.save(update_fields=["external_chat_id", "last_activity_at"])

    if is_new:
        notify(
            organization=channel.organization,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title=f"Новый диалог · {channel.name}",
            body=f"{contact.name or 'Гость'} · {integration.provider}: {inbound.text[:80]}",
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"dialog:{conversation.id}",
        )

    # AI отвечает только когда диалог ведёт AI (ADR-HUB-0003).
    if conversation.control_mode != ControlMode.AI:
        return

    try:
        result = run_channel_turn(channel=channel, message=inbound.text, history=_history(conversation))
    except ProviderError as error:
        logger.warning("AI turn failed for conversation %s: %s", conversation.id, error)
        return

    Message.objects.create(conversation=conversation, author_type=MessageAuthor.AI, text=result.text)
    conversation.last_activity_at = timezone.now()
    conversation.expected_responder = ExpectedResponder.CUSTOMER
    conversation.save(update_fields=["last_activity_at", "expected_responder"])

    transports.send_reply(
        integration, chat_id=conversation.external_chat_id, user_id=inbound.user_id, text=result.text
    )
