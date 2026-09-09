"""Файлы и фото в диалоге (дизайн-базлайн v2, композер «Прикрепить»).

Приём входящих — в ingest; здесь HTTP-слой оператора: отдача вложения и
отправка файла в диалог (Telegram, MAX, почта, Web). Правила те же, что у
текстового ответа: отправка перехватывает диалог у AI/очереди на себя.
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.http import FileResponse
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations import transports
from chatballs.conversations.models import (
    ConnectionIdentity,
    Conversation,
    ExpectedResponder,
    LifecycleState,
    Message,
    MessageAuthor,
    MessageKind,
)
from chatballs.conversations.serializers import message_payload
from chatballs.conversations.transports.base import guess_content_type, safe_filename
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.conversations.voice_views import _visible_message
from chatballs.i18n import t

MAX_FILE_BYTES = 20 * 1024 * 1024
# Исполняемые и скриптовые типы в чат не отправляем ни в одну сторону.
BLOCKED_SUFFIXES = (".exe", ".msi", ".bat", ".cmd", ".com", ".scr", ".ps1", ".vbs", ".js", ".jar", ".sh", ".dll")
INLINE_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf")


def validate_upload(upload) -> str:
    """Причина отказа или пустая строка."""
    if upload.size > MAX_FILE_BYTES:
        return "Файл больше 20 МБ"
    if not upload.size:
        return "Пустой файл"
    name = safe_filename(upload.name or "")
    if name.lower().endswith(BLOCKED_SUFFIXES):
        return "Такой тип файла отправить нельзя"
    return ""


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

    required_capability = "conversations.operate"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request, conversation_id: int) -> Response:
        from chatballs.conversations.views import claim_for_reply

        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        if conversation.lifecycle != LifecycleState.OPEN:
            return Response({"detail": t("conversations.closed")}, status=409)
        connection = conversation.connection
        if connection is None or not transports.supports_file_send(connection):
            return Response({"detail": t("conversations.files_unavailable_channel")}, status=400)
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": t("conversations.attach_file")}, status=400)
        problem = validate_upload(upload)
        if problem:
            return Response({"detail": problem}, status=400)
        name = safe_filename(upload.name or "")
        content_type = (upload.content_type or "").split(";")[0] or guess_content_type(name)
        caption = str(request.data.get("text", "")).strip()[:4000]

        claimed = claim_for_reply(self, request, conversation)
        if isinstance(claimed, Response):
            return claimed
        conversation = claimed

        identity = ConnectionIdentity.objects.filter(connection=connection, contact=conversation.contact).first()
        content = upload.read()
        sent = transports.send_file(
            connection,
            chat_id=conversation.external_chat_id,
            user_id=identity.external_user_id if identity else "",
            content=content,
            filename=name,
            content_type=content_type,
            caption=caption,
        )
        if not sent:
            return Response({"detail": t("conversations.file_send_failed")}, status=502)
        message = Message.objects.create(
            conversation=conversation,
            author_type=MessageAuthor.OPERATOR,
            author_user=request.user,
            kind=MessageKind.FILE,
            text=caption,
            attachment_name=name,
            attachment_content_type=content_type,
            attachment_size=len(content),
        )
        message.attachment.save(name, ContentFile(content), save=False)
        message.save(update_fields=["attachment"])
        conversation.last_activity_at = timezone.now()
        conversation.expected_responder = ExpectedResponder.CUSTOMER
        conversation.save(update_fields=["last_activity_at", "expected_responder"])
        self._audit(request, "file_sent", conversation)
        return Response({"message": message_payload(message)}, status=201)
