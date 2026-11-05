"""Counters over the actor's visible inbox."""

from django.db.models import Count

from chatballs.conversations.models import ControlMode, Conversation, LifecycleState
from chatballs.conversations.queue_models import policy_for
from chatballs.conversations.read_services import require_inbox_access
from chatballs.conversations.selectors import apply_conversation_visibility
from chatballs.identity.avatars import user_avatar_url
from chatballs.identity.models import HumanUser


def conversation_counters(context):
    require_inbox_access(context)
    # Чистый queryset без инбокс-аннотаций: values().annotate() иначе
    # группировал бы по _last_message_at.
    base = (
        apply_conversation_visibility(
            Conversation.objects.filter(
                organization_id=context.organization_id
            ),
            context,
        )
        .filter(archived_at__isnull=True)
        .exclude(lifecycle=LifecycleState.SPAM)
        .order_by()
    )
    open_qs = base.filter(lifecycle=LifecycleState.OPEN)
    groups = [
        {"id": row["group_id"], "name": row["group__name"], "color": row["group__color"], "count": row["count"]}
        for row in open_qs.filter(group__isnull=False)
        .values("group_id", "group__name", "group__color")
        .annotate(count=Count("id"))
        .order_by("group__name")
    ]
    ungrouped = open_qs.filter(group__isnull=True).count()
    agents = [
        {
            "id": row["channel_id"],
            "code": row["channel__code"],
            "name": row["channel__name"],
            "count": row["count"],
        }
        for row in open_qs.filter(channel__ai_agent__isnull=False).values("channel_id", "channel__code", "channel__name")
        .annotate(count=Count("id"))
        .order_by("channel__name")
    ]
    # Секция «Ответственный» поповера охвата (A1): кто сколько ведёт.
    assignees = [
        {
            "id": row["assigned_operator_id"],
            "name": row["assigned_operator__full_name"] or row["assigned_operator__email"],
            "count": row["count"],
        }
        for row in open_qs.filter(assigned_operator__isnull=False)
        .values("assigned_operator_id", "assigned_operator__full_name", "assigned_operator__email")
        .annotate(count=Count("id"))
        .order_by("-count", "assigned_operator__full_name")
    ]
    avatars = {
        user.id: user
        for user in HumanUser.objects.filter(id__in=[a["id"] for a in assignees]).exclude(avatar="")
    }
    for assignee in assignees:
        assignee["avatarUrl"] = user_avatar_url(avatars.get(assignee["id"]), context.organization.public_id)
    # Два разных ожидания (макет Q3): диалог ничей — взять может любой;
    # диалог назначен лично на меня и ждёт, пока я его возьму. Смешивать их
    # в одном счётчике значит прятать своё среди чужого.
    waiting_qs = open_qs.filter(control_mode=ControlMode.PAUSED)
    return (
        {
            "all": open_qs.count(),
            "waiting": waiting_qs.count(),
            "queue": waiting_qs.filter(assigned_operator__isnull=True).count(),
            "waitingOnMe": waiting_qs.filter(assigned_operator_id=context.actor_user.id).count(),
            # Срок личной очереди: по нему клиент считает, через сколько
            # диалог вернётся всем.
            "assignmentTimeoutMinutes": policy_for(
                context.organization
            ).assignment_timeout_minutes,
            "mine": base.filter(assigned_operator_id=context.actor_user.id).count(),
            "ungrouped": ungrouped,
            "groups": groups,
            "agents": agents,
            "assignees": assignees,
        }
    )
