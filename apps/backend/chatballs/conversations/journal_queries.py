"""One paginated internal timeline; public messages never expose these reasons."""

from django.db.models import CharField, F, Value
from rest_framework.exceptions import ValidationError

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.participant_services import participation_history
from chatballs.conversations.read_services import require_inbox_access
from chatballs.conversations.transfer_models import ConversationTransfer
from chatballs.i18n import t

FIELDS = ("recordId", "kind", "occurredAt", "actorName", "actorEmail", "subjectName", "subjectEmail", "reasonText", "commentText", "currentReasonName", "reasonActive")


def participant_events(history, *, left=False):
    prefix = "left" if left else "joined"
    actor = "left_by" if left else "joined_by"
    return history.filter(**({"left_at__isnull": False} if left else {})).order_by().annotate(
        recordId=F("id"), kind=Value("LEFT" if left else "JOINED"),
        occurredAt=F(f"{prefix}_at"), actorName=F(f"{actor}__user__full_name"),
        actorEmail=F(f"{actor}__user__email"), subjectName=F("membership__user__full_name"),
        subjectEmail=F("membership__user__email"),
        reasonText=F("leave_reason" if left else "join_reason"), commentText=Value("", output_field=CharField()),
        currentReasonName=Value("", output_field=CharField()), reasonActive=Value(True),
    ).values(*FIELDS)


def transfer_events(context, conversation_id):
    return ConversationTransfer.objects.filter(
        organization_id=context.organization_id, conversation_id=conversation_id,
    ).order_by().annotate(
        recordId=F("id"), kind=Value("TRANSFER"), occurredAt=F("occurred_at"),
        actorName=F("initiated_by__full_name"), actorEmail=F("initiated_by__email"),
        subjectName=F("new_operator__full_name"), subjectEmail=F("new_operator__email"),
        reasonText=F("reason_name"), commentText=F("comment"),
        currentReasonName=F("reason__name"), reasonActive=F("reason__is_active"),
    ).values(*FIELDS)


def journal_payload(row):
    return {
        "id": f"{row['kind']}:{row['recordId']}", "kind": row["kind"],
        "occurredAt": row["occurredAt"].isoformat(),
        "actorName": row["actorName"] or row["actorEmail"] or "",
        "subjectName": row["subjectName"] or row["subjectEmail"] or "",
        "reason": row["reasonText"], "comment": row["commentText"],
        "reasonChanged": row["kind"] == "TRANSFER" and row["currentReasonName"] != row["reasonText"],
        "reasonInactive": not row["reasonActive"],
    }


def participation_journal(context, conversation_id, params):
    require_inbox_access(context)
    history = participation_history(context=context, conversation_id=conversation_id)
    tab = params.get("kind", "all")
    if tab not in {"all", "participants", "transfers"}:
        raise ValidationError(t("conversations.not_found"))
    joined = participant_events(history)
    left = participant_events(history, left=True)
    transfers = transfer_events(context, conversation_id)
    rows = transfers if tab == "transfers" else joined.union(left)
    if tab == "all":
        rows = joined.union(left, transfers)
    rows = rows.order_by("-occurredAt", "kind", "-recordId")
    return (page_payload(paginate(rows, params), journal_payload))
