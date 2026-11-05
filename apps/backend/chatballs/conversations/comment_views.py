"""Protected, separately paginated internal history. No edit/delete surface."""

from collections.abc import Mapping

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from chatballs.conversations.comment_history import comment_history, comment_payload
from chatballs.conversations.comment_services import create_comment
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t
from chatballs.tenancy.database import tenant_atomic


class ConversationCommentsView(ConversationViewBase):
    required_capabilities = {"GET": "conversations.view", "POST": "conversations.comment"}

    def get(self, request, conversation_id):
        with tenant_atomic(request.tenant_context):
            return Response(comment_history(context=request.tenant_context,
                conversation_id=conversation_id, parameters=request.query_params))

    def post(self, request, conversation_id):
        if not isinstance(request.data, Mapping):
            raise ValidationError(t("comments.body_invalid"))
        comment, created = create_comment(
            context=request.tenant_context, conversation_id=conversation_id,
            audience=request.data.get("audience"), text=request.data.get("text"),
            operation_id=request.data.get("operationId"),
        )
        return Response({"comment": comment_payload(comment)}, status=201 if created else 200)
