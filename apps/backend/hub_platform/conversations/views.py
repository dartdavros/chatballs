from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability
from hub_platform.conversations.clients import client_detail, clients_overview
from hub_platform.conversations.command import command_center_overview
from hub_platform.conversations.models import Contact, ControlMode, Conversation, ConversationRead
from hub_platform.conversations.selectors import (
    conversation_for_context,
    conversations_for_context,
)
from hub_platform.conversations.serializers import conversation_payload, message_payload
from hub_platform.conversations.services import (
    ClaimError,
    claim_conversation,
    close_conversation,
    post_operator_message,
    release_to_ai,
    request_contact,
    return_to_queue,
)
from hub_platform.conversations.stats import sales_overview_stats
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.policy import (
    ResourceScope,
    accessible_department_ids,
    authorize,
    require_capability,
)


class _Base(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"

    def _org(self, request: Request):
        return request.tenant_context.organization

    def _conversation(
        self,
        request: Request,
        conversation_id: int,
        capability: str = "conversations.view",
    ) -> Conversation:
        conversation = conversation_for_context(
            context=request.tenant_context, conversation_id=conversation_id
        )
        if not require_capability(request.tenant_context.membership, capability, conversation):
            raise Conversation.DoesNotExist
        return conversation

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
        items = conversations_for_context(request.tenant_context)
        department_ids = accessible_department_ids(request.tenant_context.membership, self.required_capability)
        if department_ids is not None:
            items = items.filter(channel__department_id__in=department_ids)
        department = request.query_params.get("department")
        if department:
            items = items.filter(channel__department__code=department)
        lifecycle = request.query_params.get("lifecycle")
        if lifecycle:
            items = items.filter(lifecycle=lifecycle)
        items = list(items)
        # Отметки прочтения просматривающего: бейдж считается персонально.
        read_map = dict(
            ConversationRead.objects.filter(user=request.user, conversation__in=items)
            .values_list("conversation_id", "last_read_message_id")
        )
        return Response({"items": [conversation_payload(c, last_read_id=read_map.get(c.id, 0)) for c in items]})


class ConversationDetailView(_Base):
    def get(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        # Открытие диалога = прочтение: двигаем персональную отметку до последнего
        # сообщения (detail поллится каждые 3 с — пишем только при продвижении).
        last_id = conversation.messages.order_by("-id").values_list("id", flat=True).first() or 0
        if last_id:
            read, created = ConversationRead.objects.get_or_create(
                conversation=conversation, user=request.user, defaults={"last_read_message_id": last_id}
            )
            if not created and read.last_read_message_id < last_id:
                read.last_read_message_id = last_id
                read.save(update_fields=["last_read_message_id", "updated_at"])
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationClaimView(_Base):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        try:
            conversation = claim_conversation(
                context=request.tenant_context, conversation_id=conversation_id
            )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        self._audit(request, "claimed", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationReleaseView(_Base):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        conversation = release_to_ai(
            context=request.tenant_context, conversation_id=conversation_id
        )
        self._audit(request, "released_to_ai", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationReturnQueueView(_Base):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        conversation = return_to_queue(
            context=request.tenant_context, conversation_id=conversation_id
        )
        self._audit(request, "returned_to_queue", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})


class ConversationStatsView(_Base):
    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        department_ids = accessible_department_ids(request.tenant_context.membership, self.required_capability)
        return Response(sales_overview_stats(request.tenant_context, period, department_ids))


class CommandOverviewView(_Base):
    required_capability = "company.view"
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        return Response(command_center_overview(request.tenant_context, period))


class ClientsView(_Base):
    required_capability = "customers.view"

    def get(self, request: Request) -> Response:
        department_ids = accessible_department_ids(request.tenant_context.membership, self.required_capability)
        return Response({"items": clients_overview(self._org(request).id, department_ids)})


class ClientDetailView(_Base):
    required_capability = "customers.view"

    def get(self, request: Request, contact_id: int) -> Response:
        try:
            department_ids = accessible_department_ids(request.tenant_context.membership, self.required_capability)
            return Response(
                {"client": client_detail(self._org(request).id, contact_id, department_ids)}
            )
        except Contact.DoesNotExist:
            return Response({"detail": "Клиент не найден"}, status=404)


class ConversationMessageView(_Base):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        text = str(request.data.get("text", "")).strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=400)
        if conversation.control_mode != ControlMode.HUMAN:
            return Response({"detail": "Сначала перехватите диалог"}, status=409)
        manager_override = authorize(
            request.tenant_context.membership,
            self.required_capability,
            ResourceScope(conversation.organization_id),
        )
        if conversation.assigned_operator_id != request.user.id and not manager_override:
            return Response({"detail": "Диалог ведёт другой оператор"}, status=409)
        message = post_operator_message(
            context=request.tenant_context, conversation=conversation, text=text
        )
        return Response({"message": message_payload(message)}, status=201)


class ConversationRequestContactView(_Base):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        if not conversation.contact_id or not conversation.connection_id:
            return Response({"detail": "У диалога нет канала для запроса контакта"}, status=409)
        if conversation.contact.phone:
            return Response({"detail": "Контакт уже получен"}, status=409)
        message = request_contact(context=request.tenant_context, conversation=conversation)
        self._audit(request, "contact_requested", conversation)
        return Response({"message": message_payload(message)}, status=201)


class ConversationCloseView(_Base):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        conversation = close_conversation(
            context=request.tenant_context, conversation_id=conversation_id
        )
        self._audit(request, "closed", conversation)
        return Response({"conversation": conversation_payload(conversation, with_messages=True)})
