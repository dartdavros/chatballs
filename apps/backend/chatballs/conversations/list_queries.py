from django.db.models import Exists, OuterRef
from rest_framework.exceptions import PermissionDenied

from chatballs.api.pagination import (
    cursor_id,
    window,
    window_payload,
    window_size,
)
from chatballs.conversations.models import (
    ControlMode,
    ConversationRead,
    LifecycleState,
    Message,
)
from chatballs.conversations.participant_models import ConversationParticipant
from chatballs.conversations.selectors import (
    order_conversations,
    visible_conversations_for,
)
from chatballs.conversations.serializers import (
    conversation_payload,
    last_messages_for,
    pending_counts_for,
)
from chatballs.i18n import t
from chatballs.identity.policy import can_administer_access

# Окно инбокса и окно истории: размеры продуктовые, клиент может запросить
# меньше, больше — только до потолка api.pagination.
LIST_WINDOW_SIZE = 30


def conversation_list(context, params):
    from django.db.models import Q

    items = visible_conversations_for(context)
    # «Удалённые» (архив) скрыты; просмотр архива — только администратор.
    if params.get("archived") == "1":
        if not can_administer_access(context.membership):
            raise PermissionDenied({"detail": t("conversations.archive_admin_only")})
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
        items = items.filter(assigned_operator_id=context.actor_user.id)
    elif assigned and assigned.isdigit():
        # Охват «Ответственный» в поповере админа (дизайн-базлайн v2, A1).
        items = items.filter(assigned_operator_id=int(assigned))
    if params.get("waiting") == "1":
        items = items.filter(
            lifecycle=LifecycleState.OPEN, control_mode=ControlMode.PAUSED
        )
    # Две вкладки ожидания (макет «Очередь и уведомления», кадр Q3): общая
    # очередь — диалоги без ответственного, их берёт кто угодно; «на мне» —
    # назначенные лично и ждущие, пока их возьмут.
    if params.get("queue") == "1":
        items = items.filter(
            lifecycle=LifecycleState.OPEN,
            control_mode=ControlMode.PAUSED,
            assigned_operator__isnull=True,
        )
    if params.get("waitingOnMe") == "1":
        items = items.filter(
            lifecycle=LifecycleState.OPEN,
            control_mode=ControlMode.PAUSED,
            assigned_operator_id=context.actor_user.id,
        )
    query = params.get("q", "").strip()
    if query:
        from django.contrib.postgres.search import SearchQuery, SearchVector

        # Имена — по подстроке; тексты сообщений — полнотекстовым поиском
        # (russian-конфиг, GIN-индекс conv_message_text_fts). Конфигурация
        # одна на оба языка и от языка организации не зависит: в «russian»
        # латиница отдана english_stem, а кириллица — russian_stem, так что
        # английская переписка стеммится английским стеммером. Менять её на
        # «english» нельзя — та оставит без основы русские слова.
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
    items = items.annotate(viewer_participates=Exists(ConversationParticipant.objects.active().filter(
        organization_id=context.organization_id,
        conversation_id=OuterRef("pk"), membership_id=context.membership.pk,
    )))
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
            user=context.actor_user, conversation__in=page.items
        ).values_list("conversation_id", "last_read_message_id")
    )
    # Превью и бейдж — на всю страницу разом: построчно это давало по два
    # запроса на диалог при обновлении списка раз в четыре секунды.
    conversation_ids = [conversation.id for conversation in page.items]
    previews = last_messages_for(conversation_ids)
    pending = pending_counts_for(conversation_ids, read_map)
    return window_payload(
        page,
        lambda c: conversation_payload(
            c,
            last_read_id=read_map.get(c.id, 0),
            viewer_id=context.actor_user.id,
            last_message=previews.get(c.id),
            pending_count=pending.get(c.id, 0),
        ),
        # Счётчик над списком показывает весь охват с учётом фильтров,
        # а не число уже загруженных строк.
        total=ordered.order_by().count(),
    )
