"""HTTP adapters for original conversation metadata services."""

from rest_framework.response import Response

from chatballs.conversations import metadata_services as service
from chatballs.conversations.models import Conversation
from chatballs.conversations.serializers import conversation_payload
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


class ConversationPriorityView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request, conversation_id):
        try:
            row = service.set_priority(request.tenant_context, conversation_id, request.data.get("priority", ""), request=request)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        return Response({"conversation": conversation_payload(row, detailed=True, viewer_id=request.user.pk)})


class ConversationContactView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request, conversation_id):
        try:
            row = service.change_contact(request.tenant_context, conversation_id, request.data, request=request)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        return Response({"conversation": conversation_payload(row, detailed=True, viewer_id=request.user.pk)})


class ConversationNoteView(ConversationViewBase):
    required_capability = "conversations.comment"

    def post(self, request, conversation_id):
        try:
            row = service.set_note(request.tenant_context, conversation_id, request.data.get("note", ""))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        return Response({"conversation": conversation_payload(row, detailed=True, viewer_id=request.user.pk)})


class ConversationLabelsView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request, conversation_id):
        try:
            row = service.set_labels(request.tenant_context, conversation_id, request.data.get("labelIds"))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        return Response({"conversation": conversation_payload(row, detailed=True, viewer_id=request.user.pk)})


class ConversationArchiveView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request, conversation_id):
        try:
            row = service.set_archived(request.tenant_context, conversation_id, request.data.get("archived"), request=request)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        return Response({"conversation": conversation_payload(row, detailed=True, viewer_id=request.user.pk)})
