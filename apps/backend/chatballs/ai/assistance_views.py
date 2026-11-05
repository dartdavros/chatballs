"""Employee-only assistance endpoints; no customer API or new UI."""

from rest_framework import serializers
from rest_framework.response import Response

from chatballs.ai import assistance_queries
from chatballs.ai.assistance_payload import suggestion_payload
from chatballs.ai.assistance_services import (
    reject_suggestion,
    request_suggestion,
)
from chatballs.conversations.view_base import ConversationViewBase


class RequestInput(serializers.Serializer):
    operationKey = serializers.CharField(max_length=160)
    attemptId = serializers.UUIDField(required=False)


class AssistanceListView(ConversationViewBase):
    required_capability = "conversations.operate"

    def get(self, request, conversation_id):
        return Response(assistance_queries.attempts(request.tenant_context, conversation_id))

    def post(self, request, conversation_id):
        data = RequestInput(data=request.data)
        data.is_valid(raise_exception=True)
        suggestion = request_suggestion(
            context=request.tenant_context, conversation_id=conversation_id,
            key=data.validated_data["operationKey"],
            attempt_id=data.validated_data.get("attemptId"),
        )
        return Response({"suggestion": suggestion_payload(suggestion)}, status=202)


class AssistanceDetailView(ConversationViewBase):
    required_capability = "conversations.operate"

    def get(self, request, conversation_id, attempt_id):
        return Response(assistance_queries.detail(request.tenant_context, conversation_id, attempt_id))


class AssistanceRejectView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request, conversation_id, suggestion_id):
        suggestion = reject_suggestion(
            context=request.tenant_context, conversation_id=conversation_id,
            suggestion_id=suggestion_id,
        )
        return Response({"suggestion": suggestion_payload(suggestion)})
