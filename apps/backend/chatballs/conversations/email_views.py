"""Mail continuation is a staff API, independent of visitor signals and UI."""

from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from chatballs.conversations import email_queries
from chatballs.conversations.email_attempt_models import EmailSendOperation
from chatballs.conversations.email_continuation import (
    retry_email_reply,
    send_email_reply,
)
from chatballs.conversations.email_payloads import attempt_payload, operation_payload
from chatballs.conversations.models import Conversation
from chatballs.conversations.services import ClaimError
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


class SendInput(serializers.Serializer):
    recipient = serializers.EmailField()
    connectionId = serializers.IntegerField(min_value=1)
    text = serializers.CharField(max_length=20000, required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False)
    clientKey = serializers.CharField(max_length=128)
    subject = serializers.CharField(max_length=998, required=False, allow_blank=True, default="")


class RetryInput(serializers.Serializer):
    acknowledgeUnknown = serializers.BooleanField(default=False)


class EmailOptionsView(ConversationViewBase):
    required_capability = "conversations.operate"

    def get(self, request, conversation_id):
        try:
            data = email_queries.options(request.tenant_context, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        return Response(data)


class EmailOperationsView(ConversationViewBase):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    required_capabilities = {"GET": "conversations.view", "POST": "conversations.operate"}

    def get(self, request, conversation_id):
        try:
            data = email_queries.operations(request.tenant_context, conversation_id,
                message_ids=request.query_params.get("messageIds"), before=request.query_params.get("before"),
                limit=request.query_params.get("limit", 50))
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        return Response(data)

    def post(self, request, conversation_id):
        data = SendInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        try:
            operation, created = send_email_reply(
                context=request.tenant_context, conversation_id=conversation_id,
                recipient=values["recipient"], connection_id=values["connectionId"],
                text=values["text"], client_key=values["clientKey"], subject=values["subject"],
                upload=values.get("file"),
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        return Response({"operation": operation_payload(operation, context=request.tenant_context)}, status=201 if created else 200)


class EmailRetryView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request, conversation_id, operation_id):
        data = RetryInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            attempt = retry_email_reply(
                context=request.tenant_context, conversation_id=conversation_id,
                operation_id=operation_id, acknowledge_unknown=data.validated_data["acknowledgeUnknown"],
            )
        except (Conversation.DoesNotExist, EmailSendOperation.DoesNotExist):
            return Response({"detail": t("conversations.not_found")}, status=404)
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        return Response({"attempt": attempt_payload(attempt)}, status=201)
