"""Диалоги: контакты, идентичности, метки, шаблоны, диалоги во всех состояниях,
сообщения (текст, системные, контакт, голосовые), прочтения, веб-гость."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.core.files.base import ContentFile

from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    ConversationLabel,
    Conversation,
    ConversationRead,
    Message,
    MessageAuthor,
    MessageKind,
    ReplyTemplate,
    TranscriptStatus,
)
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate, moment, now
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.services import issue_session

logger = logging.getLogger(__name__)

AVATAR_URL = "/api/v1/demo-media/avatars/{name}"


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("conversations")
    organization = refs.organization
    current = now()

    for item in data["contacts"]:
        contact, created = Contact.objects.get_or_create(
            organization=organization,
            name=item["name"],
            defaults={
                "phone": item.get("phone", ""),
                "avatar_url": AVATAR_URL.format(name=item["avatar"]) if item.get("avatar") else "",
                "description": item.get("description", ""),
                "company": item.get("company", ""),
                "city": item.get("city", ""),
            },
        )
        if created:
            backdate(contact, moment(item, current, "created"))
        refs.contacts[item["key"]] = contact

    for item in data["connectionIdentities"]:
        _ensure_identity(refs, item)

    for item in data.get("labels", []):
        label, _ = ConversationLabel.objects.get_or_create(
            organization=organization, name=item["name"], defaults={"color": item.get("color", "")}
        )
        refs.labels[item["key"]] = label

    for item in data.get("replyTemplates", []):
        ReplyTemplate.objects.get_or_create(
            organization=organization, title=item["title"], defaults={"text": item["text"]}
        )

    # Объединение контактов (ADR-HUB-0006): демо показывает и историю слияний.
    for item in data.get("contactMerges", []):
        _merge_contacts(context, refs, item)

    # Диалоги с previousConversation ссылаются на более ранние — создаём в два прохода.
    pending = list(data["conversations"])
    created_keys: set[str] = set()
    while pending:
        progressed = False
        for item in list(pending):
            previous_key = item.get("previousConversation")
            if previous_key and previous_key not in created_keys:
                continue
            _ensure_conversation(context, refs, item, current)
            created_keys.add(item["key"])
            pending.remove(item)
            progressed = True
        if not progressed:
            raise manifest.ManifestError(
                "conversations: previousConversation forms a cycle or points to an unknown key"
            )


def _merge_contacts(context: TenantContext, refs: DemoRefs, item: dict) -> None:
    from chatballs.conversations.contacts_merge import merge_contacts
    from chatballs.conversations.models import ContactMerge

    target = refs.contacts[item["target"]]
    source = refs.contacts[item["source"]]
    if ContactMerge.objects.filter(target=target, source=source).exists():
        return
    merge_contacts(
        organization=refs.organization,
        target_id=target.id,
        source_id=source.id,
        reason=item["reason"],
        actor=refs.users.get(item.get("actor")),
    )


def _ensure_identity(refs: DemoRefs, item: dict) -> None:
    connection = refs.integrations[item["connection"]]
    contact = refs.contacts[item["contact"]]
    identity, _ = ConnectionIdentity.objects.get_or_create(
        connection=connection,
        external_user_id=item["externalUserId"],
        defaults={
            "organization": refs.organization,
            "contact": contact,
            "display_name": item.get("displayName", ""),
            "username": item.get("username", ""),
        },
    )
    refs.identities[item["key"]] = identity


def _web_guest(context: TenantContext, refs: DemoRefs, item: dict) -> tuple[Contact, ConnectionIdentity, str]:
    """Анонимный гость виджета: настоящая веб-сессия через сервис webchat."""
    widget = refs.widgets[item["connection"]]
    session = issue_session(context=context, widget=widget)
    if session is None:
        raise manifest.ManifestError("web widget has no channel — cannot issue guest session")
    identity = ConnectionIdentity.objects.get(
        connection=refs.integrations[item["connection"]], external_user_id=session["sessionId"]
    )
    contact = identity.contact
    # Гость, который представился в виджете (кадр B: «Дмитрий Орлов», Web Chat).
    if item.get("guestName") or item.get("guestAvatar"):
        if item.get("guestName"):
            contact.name = item["guestName"]
        if item.get("guestAvatar"):
            contact.avatar_url = AVATAR_URL.format(name=item["guestAvatar"])
        contact.save(update_fields=["name", "avatar_url"])
    return contact, identity, session["sessionId"]


def _ensure_conversation(context: TenantContext, refs: DemoRefs, item: dict, current) -> None:
    organization = refs.organization
    channel = refs.channels[item["agent"]]
    connection = refs.integrations[item["connection"]]
    if item.get("webGuest"):
        contact, identity, external_chat_id = _web_guest(context, refs, item)
    else:
        contact = refs.contacts.get(item.get("contact"))
        identity = refs.identities.get(item.get("identity"))
        external_chat_id = item["externalChatId"]

    existing = Conversation.objects.filter(
        organization=organization, channel=channel, external_chat_id=external_chat_id
    ).order_by("-id")
    # Один и тот же чат может иметь несколько диалогов (история контакта):
    # ключ уникальности — чат + момент создания.
    created_at = moment(item, current, "created") or current
    conversation = existing.filter(created_at=created_at).first()
    if conversation is not None:
        refs.conversations[item["key"]] = conversation
        return

    snapshot = refs.identity_snapshots.get(item.get("supportIdentitySnapshot"))
    conversation = Conversation.objects.create(
        organization=organization,
        channel=channel,
        connection=connection,
        # Ровно одна личность: снимок из личного кабинета либо контакт.
        contact=None if snapshot is not None else contact,
        support_identity_snapshot=snapshot,
        external_chat_id=external_chat_id,
        transport_meta=item.get("transportMeta", {}),
        lifecycle=item.get("lifecycle", "OPEN"),
        control_mode=item.get("controlMode", "AI"),
        expected_responder=item.get("expectedResponder", "AI"),
        group=refs.groups.get(item.get("group")),
        assigned_operator=refs.users.get(item.get("assignedOperator")),
        priority=item.get("priority", "NONE"),
        note=item.get("note", ""),
        previous_conversation=refs.conversations.get(item.get("previousConversation")),
    )
    for label_key in item.get("labels", []):
        label = refs.labels.get(label_key)
        if label is not None:
            conversation.labels.add(label)
    archived_at = moment(item, current, "archived")
    if archived_at is not None:
        Conversation.objects.filter(pk=conversation.pk).update(archived_at=archived_at)
    last_activity = moment(item, current, "lastActivity") or created_at
    backdate(conversation, created_at, "created_at")
    backdate(conversation, last_activity, "last_activity_at")
    refs.conversations[item["key"]] = conversation

    last_message: Message | None = None
    for index, spec in enumerate(item.get("messages", []), start=1):
        message = _create_message(context, refs, conversation, spec, index, current)
        if message is not None:
            last_message = message

    if last_message is not None:
        for reader_key in item.get("readBy", []):
            user = refs.users.get(reader_key)
            if user is not None:
                ConversationRead.objects.update_or_create(
                    conversation=conversation,
                    user=user,
                    defaults={"last_read_message_id": last_message.id},
                )


def _create_message(context: TenantContext, refs: DemoRefs, conversation: Conversation, spec: dict, index: int, current) -> Message | None:
    author_type = spec["author"]
    kind = spec.get("kind", MessageKind.TEXT)
    voice = spec.get("voice")
    if kind == MessageKind.VOICE and voice is not None:
        filename = f"voice/{voice['file']}"
        if not manifest.media_exists(filename):
            logger.warning("Demo voice file %s is missing — message skipped", filename)
            return None
    message = Message.objects.create(
        conversation=conversation,
        author_type=author_type,
        author_user=refs.users.get(spec.get("authorUser")) if author_type == MessageAuthor.OPERATOR else None,
        kind=kind,
        text=spec.get("text", ""),
        content_html=spec.get("contentHtml", ""),
        external_id=f"demo-{conversation.id}-{index}",
    )
    if kind == MessageKind.VOICE and voice is not None:
        payload = manifest.media_bytes(f"voice/{voice['file']}")
        content_type = voice.get("contentType", "audio/ogg")
        suffix = voice["file"].rsplit(".", 1)[-1]
        message.audio_content_type = content_type
        message.duration_seconds = int(voice.get("durationSeconds", 0))
        message.transcript = voice.get("transcript", "")
        message.transcript_status = voice.get("transcriptStatus", TranscriptStatus.NONE)
        message.audio.save(f"voice.{suffix}", ContentFile(payload), save=False)
        message.save(
            update_fields=["audio", "audio_content_type", "duration_seconds", "transcript", "transcript_status"]
        )
    backdate(message, moment(spec, current) or current - timedelta(minutes=1))
    return message
