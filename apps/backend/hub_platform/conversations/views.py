from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.conversations.clients import client_detail, clients_overview
from hub_platform.conversations.models import Contact, Conversation, ControlMode
from hub_platform.conversations.selectors import conversation_for_organization, conversations_for_organization
from hub_platform.conversations.serializers import conversation_payload, message_payload
from hub_platform.conversations.stats import sales_overview_stats
from hub_platform.conversations.services import (
    ClaimError,
    claim_conversation,
    close_conversation,
    post_operator_message,
    release_to_ai,
    return_to_queue,
)
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.permissions import is_owner


class _Base(APIView):
    permission_classes = [IsAuthenticated]

    def _org(self, request: Request):
        return request.user.employee_profile.organization

    def _conversation(self, request: Request, conversation_id: int) -> Conversation:
        return conversation_for_organization(organization_id=self._org(request).id, conversation_id=conversation_id)

    def _audit(self, request: Request, action: str, conversation: Conversation) -> None:
        record_audit_event(
            action=f"conversations.{action}",
            actor=request.user,
            organization=self._org(request),
            object_type="Conversation",
            object_id=str(conversation.id),
            request=request,
        )


class ConversationListView(_Base):
    def get(self, request: Request) -> Response:
        items = conversations_for_organization(self._org(request).id)
        lifecycle = request.query_params.get("lifecycle")
        if lifecycle:
            items = items.filter(lifecycle=lifecycle)
        return Response({"items": [conversation_payload(c) for c in items]})


class ConversationDetailView(_Base):
    def get(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationClaimView(_Base):
    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        try:
            conversation = claim_conversation(conversation_id=conversation_id, operator=request.user)
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        self._audit(request, "claimed", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationReleaseView(_Base):
    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        conversation = release_to_ai(conversation_id=conversation_id)
        self._audit(request, "released_to_ai", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationReturnQueueView(_Base):
    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        conversation = return_to_queue(conversation_id=conversation_id)
        self._audit(request, "returned_to_queue", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationStatsView(_Base):
    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        return Response(sales_overview_stats(self._org(request).id, period))


class ClientsView(_Base):
    def get(self, request: Request) -> Response:
        return Response({"items": clients_overview(self._org(request).id)})


class ClientDetailView(_Base):
    def get(self, request: Request, contact_id: int) -> Response:
        try:
            return Response({"client": client_detail(self._org(request).id, contact_id)})
        except Contact.DoesNotExist:
            return Response({"detail": "Клиент не найден"}, status=404)


class ConversationMessageView(_Base):
    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        text = str(request.data.get("text", "")).strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=400)
        if conversation.control_mode != ControlMode.HUMAN:
            return Response({"detail": "Сначала перехватите диалог"}, status=409)
        if conversation.assigned_operator_id != request.user.id and not is_owner(request.user):
            return Response({"detail": "Диалог ведёт другой оператор"}, status=409)
        message = post_operator_message(conversation=conversation, operator=request.user, text=text)
        return Response({"message": message_payload(message)}, status=201)


class ConversationCloseView(_Base):
    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        conversation = close_conversation(conversation_id=conversation_id)
        self._audit(request, "closed", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})
