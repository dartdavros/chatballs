from django.db import transaction
from rest_framework.request import Request
from rest_framework.response import Response

from hub_platform.conversations.models import (
    ControlMode,
    Conversation,
    ConversationRead,
    LifecycleState,
    Message,
)
from hub_platform.conversations.selectors import visible_conversations_for
from hub_platform.conversations.serializers import conversation_payload, message_payload
from hub_platform.conversations.services import (
    ClaimError,
    claim_conversation,
    close_conversation,
    mark_conversation_as_spam,
    post_operator_message,
    release_to_ai,
    request_contact,
    return_to_queue,
)
from hub_platform.conversations.view_base import ConversationViewBase
from hub_platform.identity.group_models import EmployeeGroup
from hub_platform.identity.models import OrganizationMembership
from hub_platform.identity.policy import ResourceScope, authorize, can_administer_access


class ConversationListView(ConversationViewBase):
    def get(self, request: Request) -> Response:
        from django.db.models import Q

        params = request.query_params
        items = visible_conversations_for(request.tenant_context)
        # «Удалённые» (архив) скрыты; просмотр архива — только администратор.
        if params.get("archived") == "1":
            if not can_administer_access(request.tenant_context.membership):
                return Response({"detail": "Архив доступен администраторам"}, status=403)
            items = items.filter(archived_at__isnull=False)
        else:
            items = items.filter(archived_at__isnull=True)
        group = params.get("group")
        if group == "none":
            items = items.filter(group__isnull=True)
        elif group:
            items = items.filter(group_id=group)
        agent = params.get("agent")
        if agent:
            items = items.filter(channel_id=agent)
        lifecycle = params.get("lifecycle")
        if lifecycle:
            items = items.filter(lifecycle=lifecycle)
        else:
            # Спам не показывается в обычных вкладках (дизайн-базлайн v2).
            items = items.exclude(lifecycle=LifecycleState.SPAM)
        if params.get("assigned") == "me":
            items = items.filter(assigned_operator_id=request.user.id)
        if params.get("waiting") == "1":
            items = items.filter(
                lifecycle=LifecycleState.OPEN, control_mode=ControlMode.PAUSED
            )
        query = params.get("q", "").strip()
        if query:
            from django.contrib.postgres.search import SearchQuery, SearchVector
            from django.db.models import Exists, OuterRef

            # Имена — по подстроке; тексты сообщений — полнотекстовым поиском
            # (russian-конфиг, GIN-индекс conv_message_text_fts).
            search = SearchQuery(query, config="russian", search_type="websearch")
            message_match = (
                Message.objects.filter(conversation=OuterRef("pk"))
                .annotate(fts=SearchVector("text", config="russian"))
                .filter(fts=search)
            )
            items = items.filter(
                Q(contact__name__icontains=query)
                | Q(support_identity_snapshot__display_name__icontains=query)
                | Q(Exists(message_match))
            )
        items = list(items)
        # Отметки прочтения просматривающего: бейдж считается персонально.
        read_map = dict(
            ConversationRead.objects.filter(user=request.user, conversation__in=items)
            .values_list("conversation_id", "last_read_message_id")
        )
        return Response(
            {
                "items": [
                    conversation_payload(
                        c,
                        last_read_id=read_map.get(c.id, 0),
                        viewer_id=request.user.id,
                    )
                    for c in items
                ]
            }
        )


class ConversationDetailView(ConversationViewBase):
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
        return Response(
            {
                "conversation": conversation_payload(
                    conversation,
                    with_messages=True,
                    viewer_id=request.user.id,
                )
            }
        )


class ConversationClaimView(ConversationViewBase):
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
        return Response(
            {
                "conversation": conversation_payload(
                    conversation,
                    with_messages=True,
                    viewer_id=request.user.id,
                )
            }
        )


class ConversationReleaseView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        try:
            conversation = release_to_ai(
                context=request.tenant_context, conversation_id=conversation_id
            )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        self._audit(request, "released_to_ai", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation,
                    with_messages=True,
                    viewer_id=request.user.id,
                )
            }
        )


class ConversationReturnQueueView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        try:
            conversation = return_to_queue(
                context=request.tenant_context, conversation_id=conversation_id
            )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        self._audit(request, "returned_to_queue", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation,
                    with_messages=True,
                    viewer_id=request.user.id,
                )
            }
        )


class ConversationMessageView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        text = str(request.data.get("text", "")).strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=400)
        if conversation.lifecycle != LifecycleState.OPEN:
            return Response({"detail": "Диалог закрыт"}, status=409)
        if conversation.control_mode != ControlMode.HUMAN:
            # Одно действие взятия (дизайн-базлайн v2, решение 2; ADR-HUB-0003):
            # первое сообщение сотрудника атомарно перехватывает диалог у AI/очереди.
            try:
                with transaction.atomic():
                    conversation = claim_conversation(
                        context=request.tenant_context, conversation_id=conversation.id
                    )
            except ClaimError as error:
                return Response({"detail": str(error)}, status=409)
            self._audit(request, "claimed", conversation)
        manager_override = authorize(
            request.tenant_context.membership,
            self.required_capability,
            ResourceScope(conversation.organization_id),
        )
        if conversation.assigned_operator_id != request.user.id and not manager_override:
            return Response({"detail": "Диалог ведёт другой оператор"}, status=409)
        try:
            message = post_operator_message(
                context=request.tenant_context, conversation=conversation, text=text
            )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        return Response({"message": message_payload(message)}, status=201)


class ConversationRequestContactView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        if not conversation.contact_id or not conversation.connection_id:
            return Response({"detail": "У диалога нет канала для запроса контакта"}, status=409)
        if conversation.lifecycle != LifecycleState.OPEN:
            return Response({"detail": "Диалог закрыт"}, status=409)
        if conversation.contact.phone:
            return Response({"detail": "Контакт уже получен"}, status=409)
        try:
            message = request_contact(
                context=request.tenant_context,
                conversation=conversation,
            )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        self._audit(request, "contact_requested", conversation)
        return Response({"message": message_payload(message)}, status=201)


class ConversationCloseView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        try:
            conversation = close_conversation(
                context=request.tenant_context, conversation_id=conversation_id
            )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        self._audit(request, "closed", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation,
                    with_messages=True,
                    viewer_id=request.user.id,
                )
            }
        )


class ConversationSpamView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        try:
            conversation = mark_conversation_as_spam(
                context=request.tenant_context, conversation_id=conversation_id
            )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        self._audit(request, "marked_spam", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation,
                    with_messages=True,
                    viewer_id=request.user.id,
                )
            }
        )


class ConversationGroupView(ConversationViewBase):
    """Перенос диалога в группу и снятие группы (ADR-HUB-0043 §3)."""

    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        group_id = request.data.get("groupId")
        group = None
        if group_id is not None:
            group = EmployeeGroup.objects.filter(
                organization_id=conversation.organization_id, id=group_id
            ).first()
            if group is None:
                return Response({"detail": "Группа не найдена"}, status=400)
        conversation.group = group
        conversation.save(update_fields=["group"])
        self._audit(request, "group_changed", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, viewer_id=request.user.id
                )
            }
        )


class ConversationAssigneeView(ConversationViewBase):
    """Назначение и переназначение ответственного (ADR-HUB-0043 §3)."""

    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        user_id = request.data.get("userId")
        assignee = None
        if user_id is not None:
            membership = (
                OrganizationMembership.objects.select_related("user")
                .filter(
                    organization_id=conversation.organization_id,
                    user_id=user_id,
                    blocked_at__isnull=True,
                )
                .first()
            )
            if membership is None:
                return Response({"detail": "Сотрудник не найден"}, status=400)
            assignee = membership.user
        conversation.assigned_operator = assignee
        conversation.save(update_fields=["assigned_operator"])
        self._audit(request, "assignee_changed", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, viewer_id=request.user.id
                )
            }
        )
