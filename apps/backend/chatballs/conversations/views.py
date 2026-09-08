from django.db import transaction
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations.models import (
    ControlMode,
    Conversation,
    ConversationRead,
    LifecycleState,
    Message,
)
from chatballs.api.pagination import (
    cursor_id,
    window,
    window_payload,
    window_size,
)
from chatballs.conversations.selectors import (
    MESSAGES_NEWER_KEYS,
    MESSAGES_OLDER_KEYS,
    conversation_messages,
    order_conversations,
    visible_conversations_for,
)
from chatballs.conversations.serializers import (
    conversation_payload,
    last_messages_for,
    message_payload,
    pending_counts_for,
)
from chatballs.conversations.services import (
    ClaimError,
    claim_conversation,
    close_conversation,
    mark_conversation_as_spam,
    post_operator_message,
    release_to_ai,
    request_contact,
    return_to_queue,
)
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.policy import ResourceScope, authorize, can_administer_access

# Окно инбокса и окно истории: размеры продуктовые, клиент может запросить
# меньше, больше — только до потолка api.pagination.
LIST_WINDOW_SIZE = 30
MESSAGE_WINDOW_SIZE = 50


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
        assigned = params.get("assigned")
        if assigned == "me":
            items = items.filter(assigned_operator_id=request.user.id)
        elif assigned and assigned.isdigit():
            # Охват «Ответственный» в поповере админа (дизайн-базлайн v2, A1).
            items = items.filter(assigned_operator_id=int(assigned))
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
                | Q(Exists(message_match))
            )
        # Инбокс — живая лента: окно по курсору, а не номера страниц. Сортировка
        # серверная, иначе окно и порядок разъезжаются.
        ordered, keys = order_conversations(items, params.get("sort", "activity"))
        page = window(
            ordered,
            keys=keys,
            limit=window_size(params, default=LIST_WINDOW_SIZE),
            after=cursor_id(params),
        )
        # Отметки прочтения просматривающего: бейдж считается персонально.
        read_map = dict(
            ConversationRead.objects.filter(
                user=request.user, conversation__in=page.items
            ).values_list("conversation_id", "last_read_message_id")
        )
        # Превью и бейдж — на всю страницу разом: построчно это давало по два
        # запроса на диалог при обновлении списка раз в четыре секунды.
        conversation_ids = [conversation.id for conversation in page.items]
        previews = last_messages_for(conversation_ids)
        pending = pending_counts_for(conversation_ids, read_map)
        return Response(
            window_payload(
                page,
                lambda c: conversation_payload(
                    c,
                    last_read_id=read_map.get(c.id, 0),
                    viewer_id=request.user.id,
                    last_message=previews.get(c.id),
                    pending_count=pending.get(c.id, 0),
                ),
                # Счётчик над списком показывает весь охват с учётом фильтров,
                # а не число уже загруженных строк.
                total=ordered.order_by().count(),
            )
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
                    detailed=True,
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
                    detailed=True,
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
                    detailed=True,
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
                    detailed=True,
                    viewer_id=request.user.id,
                )
            }
        )


def claim_for_reply(view: ConversationViewBase, request: Request, conversation: Conversation) -> Conversation | Response:
    """Одно действие взятия (дизайн-базлайн v2, решение 2; ADR-CHATBALLS-0003): первая
    реплика сотрудника (текст или файл) атомарно перехватывает диалог у
    AI/очереди. Возвращает диалог или готовый ответ с ошибкой."""
    if conversation.control_mode != ControlMode.HUMAN:
        try:
            with transaction.atomic():
                conversation = claim_conversation(
                    context=request.tenant_context, conversation_id=conversation.id
                )
        except ClaimError as error:
            return Response({"detail": str(error)}, status=409)
        view._audit(request, "claimed", conversation)
    manager_override = authorize(
        request.tenant_context.membership,
        view.required_capability,
        ResourceScope(conversation.organization_id),
    )
    if conversation.assigned_operator_id != request.user.id and not manager_override:
        return Response({"detail": "Диалог ведёт другой оператор"}, status=409)
    return conversation


class ConversationMessageView(ConversationViewBase):
    # Читает историю тот, кто видит диалог; пишет — тот, кто его ведёт.
    required_capabilities = {"GET": "conversations.view", "POST": "conversations.operate"}
    required_capability = "conversations.operate"

    def get(self, request: Request, conversation_id: int) -> Response:
        """Окно истории.

        `after` — что появилось после последнего показанного сообщения (этим
        живёт обновление открытого диалога); `before` — что было до самого
        раннего показанного (этим живёт прокрутка вверх). Без курсора — хвост
        переписки, то есть последние сообщения.
        """
        try:
            conversation = self._conversation(request, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        params = request.query_params
        limit = window_size(params, default=MESSAGE_WINDOW_SIZE)
        messages = conversation_messages(conversation)
        after = cursor_id(params, "after")
        if after is not None:
            return Response(
                window_payload(
                    window(messages, keys=MESSAGES_NEWER_KEYS, limit=limit, after=after),
                    message_payload,
                )
            )
        page = window(
            messages,
            keys=MESSAGES_OLDER_KEYS,
            limit=limit,
            after=cursor_id(params, "before"),
        )
        # Курсор считается по окну «от свежих к старым» — это самое раннее
        # сообщение окна, с него продолжится прокрутка вверх. Наружу список
        # уходит в хронологическом порядке, как его рисует лента.
        payload = window_payload(page, message_payload)
        payload["items"].reverse()
        return Response(payload)

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
        claimed = claim_for_reply(self, request, conversation)
        if isinstance(claimed, Response):
            return claimed
        conversation = claimed
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
                    detailed=True,
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
                    detailed=True,
                    viewer_id=request.user.id,
                )
            }
        )


class ConversationGroupView(ConversationViewBase):
    """Перенос диалога в группу и снятие группы (ADR-CHATBALLS-0043 §3)."""

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
    """Назначение и переназначение ответственного (ADR-CHATBALLS-0043 §3)."""

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
