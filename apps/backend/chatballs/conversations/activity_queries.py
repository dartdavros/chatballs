"""Read-only activity display; access is checked against the current conversation."""

from rest_framework import serializers

from chatballs.api.pagination import paginate
from chatballs.conversations.activity_history import history_index, history_records, history_sources
from chatballs.conversations.read_services import visible_conversation
from chatballs.conversations.transfer_display import transfer_history_payload


class HistoryInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("all", "transfers", "participants"), default="all")


def person(member):
    user = member.user if member else None
    return {"id": user.pk, "name": user.full_name or user.email} if user else None


def activity_payload(item, records):
    kind = item["history_kind"]
    row = records[kind][item["id"]]
    payload = {
        "id": f"{kind}:{row.pk}", "kind": kind, "occurredAt": item["history_time"].isoformat(),
        "actor": None, "recipient": None, "reason": None, "comment": "",
    }
    if kind == "TRANSFER":
        transfer = transfer_history_payload(row)
        payload.update(actor=transfer["initiatedBy"], recipient=transfer["newOperator"],
                       reason=transfer["reason"], comment=transfer["comment"])
    elif kind in ("JOIN", "LEAVE"):
        payload.update(
            actor=person(row.joined_by if kind == "JOIN" else row.left_by), recipient=person(row.membership),
            reason={"name": row.join_reason if kind == "JOIN" else row.leave_reason},
        )
    else:
        payload["actor"] = {"id": row.author_user_id, "name": row.system_params.get("operator", "")}
    return payload


def conversation_activity(context, conversation_id, params):
    data = HistoryInput(data=params)
    data.is_valid(raise_exception=True)
    conversation = visible_conversation(context, conversation_id)
    sources = history_sources(conversation)
    page = paginate(history_index(sources, data.validated_data["kind"]), params)
    index = list(page.items)
    records = history_records(sources, index)
    return ({
        "items": [activity_payload(item, records) for item in index],
        "page": page.page, "pageSize": page.page_size, "total": page.total, "pageCount": page.page_count,
    })
