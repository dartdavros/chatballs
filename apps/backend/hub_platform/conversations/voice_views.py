"""Голосовые сообщения (дизайн-базлайн v2, кадр H).

Приём входящих — в ingest; здесь HTTP-слой оператора: отдача аудио, отправка
голосового в диалог (Telegram, MAX) и расшифровка через BYOK-провайдера организации
(решение владельца 2026-09-04).
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.http import FileResponse
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from hub_platform.ai.provider.base import ProviderError
from hub_platform.conversations import transports
from hub_platform.conversations.models import (
    ControlMode,
    Conversation,
    LifecycleState,
    Message,
    MessageAuthor,
    MessageKind,
    TranscriptStatus,
)
from hub_platform.conversations.selectors import conversation_for_context
from hub_platform.conversations.serializers import message_payload
from hub_platform.conversations.view_base import ConversationViewBase

MAX_VOICE_BYTES = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = ("audio/ogg", "audio/webm", "audio/mpeg", "audio/mp4", "audio/wav")


def _visible_message(request: Request, message_id: int) -> Message:
    """Сообщение доступно, если видим его диалог (группы/назначение/архив —
    та же модель видимости, что и у detail)."""
    message = Message.objects.select_related(
        "conversation", "conversation__channel", "conversation__connection"
    ).get(id=message_id, organization_id=request.tenant_context.organization_id)
    conversation_for_context(
        context=request.tenant_context, conversation_id=message.conversation_id
    )
    return message


class MessageAudioView(ConversationViewBase):
    def get(self, request: Request, message_id: int) -> Response:
        try:
            message = _visible_message(request, message_id)
        except (Message.DoesNotExist, Conversation.DoesNotExist):
            return Response({"detail": "Сообщение не найдено"}, status=404)
        if not message.audio:
            return Response({"detail": "Аудио недоступно"}, status=404)
        return FileResponse(
            message.audio.open("rb"),
            content_type=message.audio_content_type or "application/octet-stream",
            filename="voice-message",
        )


class MessageTranscribeView(ConversationViewBase):
    required_capability = "conversations.view"

    def post(self, request: Request, message_id: int) -> Response:
        try:
            message = _visible_message(request, message_id)
        except (Message.DoesNotExist, Conversation.DoesNotExist):
            return Response({"detail": "Сообщение не найдено"}, status=404)
        if message.kind != MessageKind.VOICE or not message.audio:
            return Response({"detail": "Это не голосовое сообщение"}, status=400)
        if message.transcript_status == TranscriptStatus.READY:
            return Response({"message": message_payload(message)})

        from django.conf import settings

        from hub_platform.ai.provider.factory import get_provider

        try:
            provider = get_provider(channel=message.conversation.channel)
            with message.audio.open("rb") as handle:
                audio = handle.read()
            transcript = provider.transcribe(
                audio=audio,
                filename=message.audio.name.rsplit("/", 1)[-1],
                content_type=message.audio_content_type or "audio/ogg",
                model=settings.CUS_AI_TRANSCRIPTION_MODEL,
            )
        except ProviderError as error:
            message.transcript_status = TranscriptStatus.FAILED
            message.save(update_fields=["transcript_status"])
            return Response({"detail": str(error)}, status=502)
        message.transcript = transcript
        message.transcript_status = TranscriptStatus.READY
        message.save(update_fields=["transcript", "transcript_status"])
        return Response({"message": message_payload(message)})


class ConversationVoiceView(ConversationViewBase):
    """Отправка голосового оператором: файл из записи в композере."""

    required_capability = "conversations.operate"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        if conversation.lifecycle != LifecycleState.OPEN:
            return Response({"detail": "Диалог закрыт"}, status=409)
        if conversation.control_mode != ControlMode.HUMAN or (
            conversation.assigned_operator_id != request.user.id
        ):
            return Response(
                {"detail": "Отправка доступна назначенному оператору"}, status=403
            )
        connection = conversation.connection
        if connection is None or not transports.supports_voice_send(connection):
            return Response(
                {"detail": "Голосовые сообщения недоступны в этом канале"}, status=400
            )
        upload = request.FILES.get("audio")
        if upload is None:
            return Response({"detail": "Прикрепите аудио"}, status=400)
        if upload.size > MAX_VOICE_BYTES:
            return Response({"detail": "Аудио больше 10 МБ"}, status=400)
        content_type = (upload.content_type or "audio/ogg").split(";")[0]
        if content_type not in ALLOWED_AUDIO_TYPES:
            return Response({"detail": "Неподдерживаемый формат аудио"}, status=400)
        try:
            duration = max(0, int(request.data.get("duration", 0)))
        except (TypeError, ValueError):
            duration = 0

        content = upload.read()
        sent = transports.send_voice(
            connection,
            chat_id=conversation.external_chat_id,
            user_id="",
            content=content,
            content_type=content_type,
            duration=duration,
        )
        if not sent:
            return Response(
                {"detail": "Не удалось отправить голосовое в канал"}, status=502
            )
        message = Message.objects.create(
            conversation=conversation,
            author_type=MessageAuthor.OPERATOR,
            author_user=request.user,
            kind=MessageKind.VOICE,
            audio_content_type=content_type,
            duration_seconds=duration,
        )
        suffix = "ogg" if "ogg" in content_type else content_type.rsplit("/", 1)[-1]
        message.audio.save(f"voice.{suffix}", ContentFile(content), save=False)
        message.save(update_fields=["audio"])
        conversation.last_activity_at = timezone.now()
        conversation.save(update_fields=["last_activity_at"])
        self._audit(request, "voice_sent", conversation)
        return Response({"message": message_payload(message)}, status=201)
