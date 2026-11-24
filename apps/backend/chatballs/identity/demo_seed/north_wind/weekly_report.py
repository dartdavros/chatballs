"""Completed work from earlier demo shifts, independent of the current inbox."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.support_timeline import conversation_observations
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.appointments import MOSCOW

_HISTORY = "weeklySupportHistory"


def seed_weekly_report(dataset, dialogs, now):
    morning = now.astimezone(MOSCOW).replace(hour=9, minute=0, second=0, microsecond=0)
    records = []
    for days_ago, volume in enumerate((4, 6, 5, 7, 4, 5), start=1):
        for index in range(volume):
            dialog = dialogs[(days_ago * 3 + index * 2) % len(dialogs)]
            at = morning - timedelta(days=days_ago) + timedelta(minutes=12 + index * 39 + days_ago * 7)
            records.append({
                "scopeDialogId": dialog.pk, "startedAt": at.isoformat(), "employee": dialog.assigned_operator_id,
                "group": dialog.group_id, "connection": dialog.connection_id, "transport": dialog.connection.provider,
                "queuedAfter": 20, "acceptedAfter": 45 + (index + days_ago) * 13,
                "firstReplyAfter": 100 + (index + days_ago) * 21, "closedAfter": 580 + index * 93 + days_ago * 37,
                "aiFirst": (index + days_ago) % 3 != 0,
            })
    dataset.shop_state[_HISTORY] = records


def weekly_report_observations(context, conversations, filters, upper):
    records = DemoDataset.objects.filter(
        organization_id=context.organization_id, status__in=(DemoDatasetStatus.INSTALLED, DemoDatasetStatus.REINSTALLING),
    ).values_list("shop_state__" + _HISTORY, flat=True).first() or ()
    if not records:
        return
    visible = set(conversations.filter(pk__in={record["scopeDialogId"] for record in records}).values_list("pk", flat=True))
    for number, record in enumerate(records):
        if record["scopeDialogId"] not in visible:
            continue
        start = datetime.fromisoformat(record["startedAt"])
        if start >= upper or start + timedelta(seconds=record["closedAfter"]) < filters.start:
            continue
        for observation in _observations(record, start, upper):
            yield f"demo-week:{number}", observation


def _observations(record, start, upper):
    def at(seconds):
        return start + timedelta(seconds=seconds)

    employee = record["employee"]
    steps = [(record["queuedAfter"], "QUEUE_ENTERED", "SYSTEM", None),
             (record["acceptedAfter"], "ACCEPTED", "HUMAN", employee),
             (record["firstReplyAfter"], "PUBLIC_REPLY", "HUMAN", employee),
             (record["closedAfter"] - 70, "PUBLIC_REPLY", "HUMAN", employee),
             (record["closedAfter"], "CLOSED", "HUMAN", employee)]
    if record["aiFirst"]:
        steps.insert(0, (12, "PUBLIC_REPLY", "AI", None))
    facts = [ConversationEvent(
        event_type=kind, sequence=sequence, occurred_at=at(seconds), actor_kind=actor,
        initiated_by_id=user, responsible_id=user, group_id=record["group"],
        connection_id=record["connection"], transport=record["transport"],
    ) for sequence, (seconds, kind, actor, user) in enumerate(steps, start=1)]
    inbound = [SimpleNamespace(pk=1, created_at=start),
               SimpleNamespace(pk=2, created_at=at(record["closedAfter"] - 180))]
    return conversation_observations(facts, inbound, upper)
