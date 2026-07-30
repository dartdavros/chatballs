"""Диалоги: контакты, идентичности подключений, диалоги, сообщения, прочтения."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from hub_platform.conversations.models import (
    ConnectionIdentity,
    Contact,
    ControlMode,
    Conversation,
    ConversationRead,
    ExpectedResponder,
    LifecycleState,
    Message,
    MessageAuthor,
)
from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("conversations")
    organization = refs.organization
    now = timezone.now()

    for item in data["contacts"]:
        contact, _ = Contact.objects.update_or_create(
            organization=organization,
            name=item["name"],
            defaults={"phone": item.get("phone", ""), "avatar_url": item.get("avatarUrl", "")},
        )
        refs.contacts[item["key"]] = contact

    for item in data["connectionIdentities"]:
        _ensure_identity(refs, item)

    for item in data["conversations"]:
        _ensure_conversation(refs, item, now)


def _ensure_identity(refs: DemoRefs, item: dict) -> None:
    connection = refs.integrations[item["connection"]]
    contact = refs.contacts[item["contact"]]
    identity, _ = ConnectionIdentity.objects.update_or_create(
        connection=connection,
        external_user_id=item["externalUserId"],
        defaults={
            "contact": contact,
            "display_name": item.get("displayName", ""),
            "username": item.get("username", ""),
        },
    )
    refs.identities[item["key"]] = identity


def _ensure_conversation(refs: DemoRefs, item: dict, now) -> None:
    organization = refs.organization
    channel = refs.channels[item["channel"]]
    contact = refs.contacts.get(item.get("contact"))
    connection = refs.integrations.get(item.get("connection"))
    snapshot = refs.identity_snapshots.get(item.get("supportIdentitySnapshot"))
    is_human = item.get("controlMode") == ControlMode.HUMAN
    operator = refs.users.get(item.get("assignedOperator")) if is_human else None

    conversation, _ = Conversation.objects.get_or_create(
        organization=organization,
        channel=channel,
        external_chat_id=item["externalChatId"],
        defaults={
            "connection": connection,
            "contact": contact,
            "support_identity_snapshot": snapshot,
            "lifecycle": item.get("lifecycle", LifecycleState.OPEN),
            "control_mode": item.get("controlMode", ControlMode.AI),
            "expected_responder": item.get("expectedResponder", ExpectedResponder.AI),
            "assigned_operator": operator,
            "transport_meta": item.get("transportMeta", {}),
        },
    )
    Conversation.objects.filter(pk=conversation.pk).update(
        last_activity_at=now - timedelta(minutes=item.get("lastActivityMinutesAgo", 0))
    )
    conversation.refresh_from_db()
    refs.conversations[item["key"]] = conversation

    last_message_id = 0
    for message in item.get("messages", []):
        author_type = message["author"]
        msg, _ = Message.objects.get_or_create(
            conversation=conversation,
            external_id=message["externalId"],
            defaults={
                "author_type": author_type,
                "author_user": refs.users.get(message.get("authorUser"))
                if author_type == MessageAuthor.OPERATOR
                else None,
                "kind": message.get("kind", ""),
                "text": message.get("text", ""),
                "content_html": message.get("contentHtml", ""),
            },
        )
        last_message_id = max(last_message_id, msg.id)

    reader_key = item.get("readBy")
    if reader_key and last_message_id:
        user = refs.users.get(reader_key)
        if user is not None:
            ConversationRead.objects.update_or_create(
                conversation=conversation,
                user=user,
                defaults={"last_read_message_id": last_message_id},
            )
