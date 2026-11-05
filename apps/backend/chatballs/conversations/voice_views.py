"""Голосовые сообщения (дизайн-базлайн v2, кадр H).

Приём входящих — в ingest; здесь HTTP-слой оператора: отдача аудио, отправка
голосового в диалог (Telegram, MAX) и расшифровка через BYOK-провайдера организации
(решение владельца 2026-09-04).
"""

from __future__ import annotations

from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.ai.provider.base import ProviderError
from chatballs.conversations.media_queries import visible_message
from chatballs.conversations.models import (
    Conversation,
    Message,
    MessageKind,
    TranscriptStatus,
)
from chatballs.conversations.reply_http import reply_response
from chatballs.conversations.serializers import message_payload
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.conversations.voice_send import (
    ALLOWED_AUDIO_TYPES as ALLOWED_AUDIO_TYPES,
)
from chatballs.conversations.voice_send import (
    MAX_VOICE_BYTES as MAX_VOICE_BYTES,
)
from chatballs.conversations.voice_send import (
    send_voice_reply,
)
from chatballs.i18n import t
from chatballs.tenancy.database import tenant_atomic


def _visible_message(request: Request, message_id: int) -> Message:
    """Сообщение доступно, если видим его диалог (группы/назначение/архив —
    та же модель видимости, что и у detail)."""
    return visible_message(request.tenant_context, message_id)


class MessageAudioView(ConversationViewBase):
    def get(self, request: Request, message_id: int) -> Response:
        try:
            message = _visible_message(request, message_id)
        except (Message.DoesNotExist, Conversation.DoesNotExist):
            return Response({"detail": t("conversations.message_not_found")}, status=404)
        if not message.audio:
            return Response({"detail": t("conversations.audio_unavailable")}, status=404)
        return FileResponse(
            message.audio.open("rb"),
            content_type=message.audio_content_type or "application/octet-stream",
            filename="voice-message",
        )


class MessageTranscribeView(ConversationViewBase):
    required_capability = "conversations.view"
    # Расшифровка идёт к провайдеру организации и ждёт ответа десятки секунд.
    # Держать на это время транзакцию нельзя: вместе с ней занято соединение из
    # пула, а пул на процесс небольшой — несколько операторов, нажавших
    # «расшифровать», встали бы поперёк всех остальных запросов. Поэтому здесь
    # транзакции открываются вручную: вокруг чтения и вокруг записи, а вызов
    # провайдера остаётся между ними (chatballs.tenancy.middleware).
    tenant_manages_own_transaction = True

    def check_permissions(self, request: Request) -> None:
        with tenant_atomic(request.tenant_context):
            super().check_permissions(request)

    def post(self, request: Request, message_id: int) -> Response:
        from chatballs.conversations.transcription import (
            mark_transcription_failed,
            prepare_transcription,
            run_transcription,
            store_transcription,
        )

        context = request.tenant_context
        with tenant_atomic(context):
            try:
                message = _visible_message(request, message_id)
            except (Message.DoesNotExist, Conversation.DoesNotExist):
                return Response({"detail": t("conversations.message_not_found")}, status=404)
            if message.kind != MessageKind.VOICE or not message.audio:
                return Response({"detail": t("conversations.not_a_voice_message")}, status=400)
            if message.transcript_status == TranscriptStatus.READY:
                return Response({"message": message_payload(message)})
            try:
                job = prepare_transcription(message.conversation.channel, message)
            except ProviderError as error:
                mark_transcription_failed(message)
                return Response({"detail": str(error)}, status=502)
            if job is None:
                return Response({"detail": t("conversations.audio_unavailable")}, status=404)

        try:
            transcript = run_transcription(job)
        except ProviderError as error:
            with tenant_atomic(context):
                mark_transcription_failed(message)
            return Response({"detail": str(error)}, status=502)

        with tenant_atomic(context):
            store_transcription(message, transcript)
            payload = message_payload(message)
        if not transcript:
            return Response({"detail": t("ai.empty_transcript")}, status=502)
        return Response({"message": payload})


class ConversationVoiceView(ConversationViewBase):
    """Отправка голосового оператором: файл из записи в композере. Правила те
    же, что у текста и файла: первая реплика перехватывает диалог у AI/очереди."""

    public_reply_kind = MessageKind.VOICE
    required_capability = "conversations.operate"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request, conversation_id: int) -> Response:
        return reply_response(send_voice_reply(context=request.tenant_context,
            conversation_id=conversation_id, upload=request.FILES.get("audio"),
            duration=request.data.get("duration", 0),
            operation_id=request.headers.get("Idempotency-Key"), request=request))
