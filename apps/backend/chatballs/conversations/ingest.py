"""Inbound ingest for messenger connections (M2a).

One inbound message -> contact/conversation/message -> AI turn (if the dialog is
AI-controlled) -> outbound reply. Idempotent via the events InboxEvent.
"""

from __future__ import annotations

import hashlib
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from chatballs.ai.limits import LimitExceeded
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.runtime import HANDOFF_TOKEN
from chatballs.channels.runtime import run_channel_turn
from chatballs.conversations import transports
from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    ControlMode,
    Conversation,
    ExpectedResponder,
    LifecycleState,
    Message,
    MessageAuthor,
    MessageKind,
    TranscriptStatus,
)
from chatballs.conversations.transports.base import InboundMessage
from chatballs.events.models import EventOwnership, InboxEvent
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


def _already_processed(context: TenantContext, source: str, external_id: str, text: str) -> bool:
    payload_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    try:
        InboxEvent.objects.create(
            source=source,
            external_event_id=external_id,
            payload_hash=payload_hash,
            ownership=EventOwnership.TENANT,
            organization=context.organization,
        )
        return False
    except IntegrityError:
        return True


def _history(conversation: Conversation) -> list[dict]:
    messages = list(conversation.messages.order_by("created_at"))
    prior = messages[:-1][-_HISTORY_LIMIT:]  # без только что сохранённого входящего
    # Голосовые попадают в контекст стенограммой.
    return [{"role": _ROLE.get(m.author_type, "user"), "content": m.text or m.transcript} for m in prior if m.text or m.transcript]


def transcribe_voice_message(channel, message: Message, *, raise_errors: bool = False) -> str:
    """Стенограмма голосового через BYOK-провайдера организации; пустая строка,
    если провайдер не умеет или недоступен (статус FAILED — оператор повторит кнопкой)."""
    from chatballs.ai.provider.factory import get_provider
    from chatballs.ai.provider.routing import DEFAULT_TRANSCRIPTION_MODEL, resolve_transcription_model

    if not message.audio:
        return ""
    try:
        provider = get_provider(channel=channel)
        try:
            model = resolve_transcription_model(channel)
        except ProviderError:
            model = DEFAULT_TRANSCRIPTION_MODEL  # тестовый провайдер без интеграции
        with message.audio.open("rb") as handle:
            audio = handle.read()
        transcript = provider.transcribe(
            audio=audio,
            filename=message.audio.name.rsplit("/", 1)[-1],
            content_type=message.audio_content_type or "audio/ogg",
            model=model,
        ).strip()
    except ProviderError as error:
        logger.info("Voice transcription unavailable for message %s: %s", message.id, error)
        message.transcript_status = TranscriptStatus.FAILED
        message.save(update_fields=["transcript_status"])
        if raise_errors:
            raise
        return ""
    message.transcript = transcript
    message.transcript_status = TranscriptStatus.READY if transcript else TranscriptStatus.FAILED
    message.save(update_fields=["transcript", "transcript_status"])
    return transcript


def ingest_inbound(integration, inbound: InboundMessage) -> None:
    channel = integration.channel
    if channel is None:
        logger.warning("Integration %s has no channel — inbound dropped", integration.id)
        return
    context = TenantContext.for_resource(channel.organization)
    agent = getattr(channel, "ai_agent", None)
    ai_available = bool(agent and agent.is_active)
    source = f"{integration.provider.lower()}:{integration.id}"
    if _already_processed(context, source, inbound.external_id, inbound.text):
        return

    # Явный шаринг контакта: сообщение без текста, но с телефоном.
    is_contact_share = bool(inbound.phone)
    is_voice = bool(inbound.voice_file_id or inbound.voice_url or inbound.voice_content)
    files = tuple(inbound.files or ())
    # Файлы без текста: сообщение-контейнер не создаём, каждый файл — своя реплика.
    files_only = bool(files) and not inbound.text and not is_contact_share and not is_voice
    message_text = inbound.text or (
        f"Поделился контактом: {inbound.phone}" if is_contact_share else ""
    ) or ("Голосовое сообщение" if is_voice else "") or (
        ("Фото" if files[0].is_image else f"Файл: {files[0].name}") if files else ""
    )

    with transaction.atomic():
        identity = (
            ConnectionIdentity.objects.select_related("contact")
            .filter(connection=integration, external_user_id=inbound.user_id)
            .first()
        )
        if identity is None:
            contact = Contact.objects.create(
                organization=channel.organization,
                name=inbound.display_name,
                avatar_url=inbound.avatar_url,
            )
            identity = ConnectionIdentity.objects.create(
                contact=contact,
                connection=integration,
                external_user_id=inbound.user_id,
                display_name=inbound.display_name,
                username=inbound.username,
            )
        elif inbound.username and identity.username != inbound.username:
            identity.username = inbound.username
            identity.save(update_fields=["username"])
        contact = identity.contact
        if is_contact_share and contact.phone != inbound.phone:
            contact.phone = inbound.phone
            contact.save(update_fields=["phone"])
        # Аватар обновляем при каждом заходе: провайдер может сменить фото,
        # а контакт ещё не шарил телефон (is_contact_share=False).
        if inbound.avatar_url and contact.avatar_url != inbound.avatar_url:
            contact.avatar_url = inbound.avatar_url
            contact.save(update_fields=["avatar_url"])

        conversation = (
            Conversation.objects.filter(channel=channel, contact=contact, lifecycle=LifecycleState.OPEN)
            .order_by("-last_activity_at")
            .first()
        )
        is_new = conversation is None
        if conversation is None:
            # ADR-HUB-0002: новое сообщение после закрытия создаёт новый диалог,
            # связанный с предыдущим для навигации по истории.
            previous = Conversation.objects.filter(channel=channel, contact=contact).order_by("-created_at").first()
            conversation = Conversation.objects.create(
                organization=channel.organization,
                channel=channel,
                # Диалог наследует группу канала при создании (ADR-HUB-0043 §3).
                group=channel.group,
                connection=integration,
                contact=contact,
                external_chat_id=inbound.chat_id,
                control_mode=ControlMode.AI if ai_available else ControlMode.PAUSED,
                expected_responder=ExpectedResponder.AI if ai_available else ExpectedResponder.OPERATOR,
                previous_conversation=previous,
            )
        elif inbound.chat_id and not conversation.external_chat_id:
            conversation.external_chat_id = inbound.chat_id

        if not files_only:
            message = Message.objects.create(
                conversation=conversation,
                author_type=MessageAuthor.CONTACT,
                kind=(
                    MessageKind.CONTACT
                    if is_contact_share
                    else MessageKind.VOICE
                    if is_voice
                    else MessageKind.TEXT
                ),
                text="" if is_voice else message_text,
                content_html=inbound.content_html,
                external_id=inbound.external_id,
            )
            if is_voice:
                _store_voice(integration, inbound, message)
        for index, inbound_file in enumerate(files):
            file_message = Message.objects.create(
                conversation=conversation,
                author_type=MessageAuthor.CONTACT,
                kind=MessageKind.FILE,
                external_id=f"{inbound.external_id}:file:{index}" if not files_only or index else inbound.external_id,
            )
            _store_attachment(integration, inbound_file, file_message)
        conversation.last_activity_at = timezone.now()
        update_fields = ["external_chat_id", "last_activity_at"]
        if conversation.control_mode == ControlMode.AI and not ai_available:
            conversation.control_mode = ControlMode.PAUSED
            conversation.expected_responder = ExpectedResponder.OPERATOR
            update_fields.extend(["control_mode", "expected_responder"])
        if inbound.thread_meta:
            # Email: Message-ID последнего входящего — для ответа в тред;
            # тема диалога фиксируется по первому письму (ADR-HUB-0035).
            current = conversation.transport_meta or {}
            conversation.transport_meta = {
                **current,
                **inbound.thread_meta,
                "subject": current.get("subject") or inbound.thread_meta.get("subject", ""),
            }
            update_fields.append("transport_meta")
        conversation.save(update_fields=update_fields)

    if is_new:
        notify(
            context=context,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title=f"Новый диалог · {channel.name}",
            body=f"{contact.name or 'Гость'} · {integration.provider}: {message_text[:80]}",
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"dialog:{conversation.id}",
        )
    elif conversation.control_mode != ControlMode.AI:
        # Клиент написал в диалог, который ведёт оператор или который в очереди — пуш.
        operator = conversation.assigned_operator
        notify(
            context=context,
            type=NotificationType.DIALOG_NEW_MESSAGE,
            audience=NotificationAudience.USER if operator else NotificationAudience.OPERATORS,
            recipient_user=operator,
            title=f"Новое сообщение · {contact.name or 'Гость'}",
            body=message_text[:120],
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"msg:{integration.id}:{inbound.external_id}",
        )

    # Полученный контакт: телефон сохранён — подтверждаем (в TG заодно убираем
    # reply-клавиатуру) и не запускаем AI-ход: отвечать не на что.
    if is_contact_share:
        ack = "Спасибо! Контакт получен."
        Message.objects.create(conversation=conversation, author_type=MessageAuthor.AI, text=ack)
        conversation.expected_responder = ExpectedResponder.CUSTOMER if conversation.control_mode == ControlMode.AI else conversation.expected_responder
        conversation.save(update_fields=["expected_responder"])
        transports.send_contact_ack(integration, chat_id=conversation.external_chat_id, user_id=inbound.user_id, text=ack)
        return

    # Голосовое: AI отвечает текстом по стенограмме (BYOK-провайдер). Если
    # расшифровка недоступна, а также для файлов без текста — диалог уходит
    # оператору, как при недоступном AI, но без имитации сбоя.
    ai_input = inbound.text
    if is_voice and conversation.control_mode == ControlMode.AI and ai_available:
        ai_input = transcribe_voice_message(channel, message)
    if (is_voice and not ai_input) or files_only:
        if conversation.control_mode == ControlMode.AI:
            conversation.control_mode = ControlMode.PAUSED
            conversation.expected_responder = ExpectedResponder.OPERATOR
            conversation.save(update_fields=["control_mode", "expected_responder"])
            if is_new:
                return
            notify(
                context=context,
                type=NotificationType.DIALOG_WAITING,
                audience=NotificationAudience.OPERATORS,
                title=f"Нужен оператор · {contact.name or 'Гость'}",
                body="Голосовое без расшифровки" if is_voice else message_text[:120],
                target_id=conversation.id,
                source_type="Conversation",
                source_id=conversation.id,
                dedup_key=f"media:{conversation.id}",
            )
        return

    # Операторский канал без активного агента сразу создаёт очередь и не
    # имитирует сбой AI перед клиентом.
    if conversation.control_mode != ControlMode.AI:
        return

    try:
        result = run_channel_turn(channel=channel, message=ai_input, history=_history(conversation))
    except (ProviderError, LimitExceeded) as error:
        # Сбой AI (провайдер недоступен) или срабатывание лимита стоимости не должны
        # «терять» сообщение: переводим диалог в очередь к оператору, уведомляем и
        # отвечаем клиенту понятным fallback.
        logger.warning("AI turn failed for conversation %s: %s", conversation.id, error)
        conversation.control_mode = ControlMode.PAUSED
        conversation.expected_responder = ExpectedResponder.OPERATOR
        conversation.last_activity_at = timezone.now()
        conversation.save(update_fields=["control_mode", "expected_responder", "last_activity_at"])
        Message.objects.create(conversation=conversation, author_type=MessageAuthor.SYSTEM, text="AI недоступен — диалог передан оператору")
        fallback = "Извините, прямо сейчас не получается ответить. Я передал ваш вопрос специалисту — он скоро подключится."
        Message.objects.create(conversation=conversation, author_type=MessageAuthor.AI, text=fallback)
        notify(
            context=context,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title=f"Нужен оператор · {contact.name or 'Гость'}",
            body="AI временно недоступен, диалог ждёт ответа",
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"aifail:{conversation.id}",
        )
        notify_management(
            context=context,
            type=NotificationType.INTEGRATION_ERROR,
            title=f"Ошибка AI · {channel.name}",
            body="AI временно недоступен, диалог передан оператору",
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"aierror:{conversation.id}",
        )
        transports.send_reply(integration, chat_id=conversation.external_chat_id, user_id=inbound.user_id, text=fallback)
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
        Message.objects.create(conversation=conversation, author_type=MessageAuthor.SYSTEM, text="AI передал диалог оператору")
        notify(
            context=context,
            type=NotificationType.DIALOG_WAITING,
            audience=NotificationAudience.OPERATORS,
            title=f"AI передал диалог · {contact.name or 'Гость'}",
            body=ai_input[:120],
            target_id=conversation.id,
            source_type="Conversation",
            source_id=conversation.id,
            dedup_key=f"handoff:{conversation.id}",
        )

    if reply:
        transports.send_reply(
            integration, chat_id=conversation.external_chat_id, user_id=inbound.user_id, text=reply
        )


def _store_attachment(integration, inbound_file, message: Message) -> None:
    """Скачивание и сохранение файла/фото. Сбой скачивания не теряет сообщение:
    остаётся текстовая заглушка с именем файла."""
    from django.core.files.base import ContentFile

    try:
        content, content_type = transports.download_file(integration, inbound_file)
    except Exception as error:  # noqa: BLE001 - провайдер/сеть, деградация мягкая
        logger.warning("Attachment download failed for message %s: %s", message.id, error)
        message.kind = MessageKind.TEXT
        message.text = f"Файл «{inbound_file.name or 'без имени'}» (не удалось загрузить)"
        message.save(update_fields=["kind", "text"])
        return
    name = inbound_file.name or ("photo.jpg" if inbound_file.is_image else "file")
    message.attachment_name = name
    message.attachment_content_type = content_type
    message.attachment_size = len(content)
    message.attachment.save(name, ContentFile(content), save=False)
    message.save(update_fields=["attachment", "attachment_name", "attachment_content_type", "attachment_size"])


def _store_voice(integration, inbound: InboundMessage, message: Message) -> None:
    """Скачивание и сохранение голосового. Сбой скачивания не теряет сообщение:
    остаётся текстовая заглушка без аудио."""
    from django.core.files.base import ContentFile

    try:
        content, content_type = transports.download_voice(integration, inbound)
    except Exception as error:  # noqa: BLE001 - провайдер/сеть, деградация мягкая
        logger.warning(
            "Voice download failed for message %s: %s", message.id, error
        )
        message.kind = MessageKind.TEXT
        message.text = "Голосовое сообщение (не удалось загрузить)"
        message.save(update_fields=["kind", "text"])
        return
    suffix = "ogg" if "ogg" in content_type else content_type.rsplit("/", 1)[-1][:8] or "bin"
    message.audio_content_type = content_type
    message.duration_seconds = inbound.voice_duration
    message.audio.save(f"voice.{suffix}", ContentFile(content), save=False)
    message.save(update_fields=["audio", "audio_content_type", "duration_seconds"])
