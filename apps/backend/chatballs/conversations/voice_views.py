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

from chatballs.ai.provider.base import ProviderError
from chatballs.conversations import transports
from chatballs.conversations.models import (
    ConnectionIdentity,
    Conversation,
    ExpectedResponder,
    LifecycleState,
    Message,
    MessageAuthor,
    MessageKind,
    TranscriptStatus,
)
from chatballs.conversations.selectors import conversation_for_context
from chatballs.conversations.serializers import message_payload
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t
from chatballs.integrations.features import voice_messages_allowed
from chatballs.tenancy.database import tenant_atomic

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

    def post(self, request: Request, message_id: int) -> Response:
        from chatballs.conversations.ingest import (
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

    required_capability = "conversations.operate"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request, conversation_id: int) -> Response:
        from chatballs.conversations.views import claim_for_reply

        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        if conversation.lifecycle != LifecycleState.OPEN:
            return Response({"detail": t("conversations.closed")}, status=409)
        connection = conversation.connection
        if connection is None or not transports.supports_voice_send(connection):
            return Response(
                {"detail": t("conversations.voice_unavailable_channel")}, status=400
            )
        if not voice_messages_allowed(connection):
            return Response({"detail": t("conversations.voice_off_entry_point")}, status=400)
        upload = request.FILES.get("audio")
        if upload is None:
            return Response({"detail": t("conversations.attach_audio")}, status=400)
        if upload.size > MAX_VOICE_BYTES:
            return Response({"detail": t("conversations.audio_too_large")}, status=400)
        content_type = (upload.content_type or "audio/ogg").split(";")[0]
        if content_type not in ALLOWED_AUDIO_TYPES:
            return Response({"detail": t("conversations.audio_format_unsupported")}, status=400)
        try:
            duration = max(0, int(request.data.get("duration", 0)))
        except (TypeError, ValueError):
            duration = 0

        claimed = claim_for_reply(self, request, conversation)
        if isinstance(claimed, Response):
            return claimed
        conversation = claimed

        identity = ConnectionIdentity.objects.filter(connection=connection, contact=conversation.contact).first()
        content = upload.read()
        sent = transports.send_voice(
            connection,
            chat_id=conversation.external_chat_id,
            user_id=identity.external_user_id if identity else "",
            content=content,
            content_type=content_type,
            duration=duration,
        )
        if not sent:
            return Response(
                {"detail": t("conversations.voice_send_failed")}, status=502
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
        conversation.expected_responder = ExpectedResponder.CUSTOMER
        conversation.save(update_fields=["last_activity_at", "expected_responder"])
        self._audit(request, "voice_sent", conversation)
        return Response({"message": message_payload(message)}, status=201)
