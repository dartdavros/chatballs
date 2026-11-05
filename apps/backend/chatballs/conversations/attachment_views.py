"""Файлы и фото в диалоге (дизайн-базлайн v2, композер «Прикрепить»).

Приём входящих — в ingest; здесь HTTP-слой оператора: отдача вложения и
отправка файла в диалог (Telegram, MAX, почта, Web). Правила те же, что у
текстового ответа: отправка перехватывает диалог у AI/очереди на себя.
"""

from __future__ import annotations

from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations.attachment_policy import MAX_FILE_BYTES as MAX_FILE_BYTES
from chatballs.conversations.attachment_policy import validate_upload as validate_upload
from chatballs.conversations.attachment_send import send_attachment_reply
from chatballs.conversations.models import (
    Conversation,
    Message,
    MessageKind,
)
from chatballs.conversations.reply_http import reply_response
from chatballs.conversations.transports.base import guess_content_type
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.conversations.voice_views import _visible_message
from chatballs.i18n import t

INLINE_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf")


def attachment_response(message: Message, *, inline: bool = False) -> FileResponse:
    content_type = message.attachment_content_type or guess_content_type(message.attachment_name)
    return FileResponse(
        message.attachment.open("rb"),
        content_type=content_type,
        as_attachment=not (inline and content_type in INLINE_TYPES),
        filename=message.attachment_name or "file",
    )


class MessageAttachmentView(ConversationViewBase):
    def get(self, request: Request, message_id: int) -> Response:
        try:
            message = _visible_message(request, message_id)
        except (Message.DoesNotExist, Conversation.DoesNotExist):
            return Response({"detail": t("conversations.message_not_found")}, status=404)
        if message.kind != MessageKind.FILE or not message.attachment:
            return Response({"detail": t("conversations.file_unavailable")}, status=404)
        return attachment_response(message, inline="inline" in request.GET)


class ConversationAttachmentView(ConversationViewBase):
    """Отправка файла оператором: multipart `file` + необязательная подпись `text`."""

    public_reply_kind = MessageKind.FILE
    required_capability = "conversations.operate"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request, conversation_id: int) -> Response:
        return reply_response(send_attachment_reply(context=request.tenant_context,
            conversation_id=conversation_id, upload=request.FILES.get("file"),
            text=request.data.get("text", ""),
            operation_id=request.headers.get("Idempotency-Key"), request=request))
