"""The sole calculation entry point for HTTP, CSV and XLSX."""

from collections import defaultdict

from django.db.models import Count
from django.utils import timezone

from chatballs.conversations.domain_event_models import (
    ConversationEvent,
    ConversationEventHistoryStart,
)
from chatballs.conversations.models import Message
from chatballs.conversations.support_access import report_scope
from chatballs.conversations.support_feedback import report_feedback
from chatballs.conversations.support_metrics import Metrics
from chatballs.conversations.support_status_report import team_status_report
from chatballs.conversations.support_timeline import conversation_observations
from chatballs.identity.demo_seed.north_wind.weekly_report import weekly_report_observations
from chatballs.tenancy.database import tenant_atomic


def _load(conversations, filters, *, waiting=False):
    current = conversations.filter(lifecycle="OPEN", assigned_operator_id__isnull=False)
    if waiting:
        current = current.filter(expected_responder="OPERATOR")
    for name, field in (("employee", "assigned_operator_id"), ("group", "group_id"),
                        ("connection", "connection_id"), ("transport", "connection__provider")):
        value = getattr(filters, name)
        if value is not None:
            current = current.filter(**{field: value})
    return dict(current.values("assigned_operator_id").annotate(count=Count("pk", distinct=True))
                .values_list("assigned_operator_id", "count"))


def calculate_support_report(*, context, filters):
    with tenant_atomic(context):
        context, conversations, members = report_scope(context, filters)
        now = timezone.now()
        upper = min(now, filters.end)
        boundary = ConversationEventHistoryStart.objects.filter(pk=1).first()
        available = max(boundary.available_from, boundary.sources_available_from) if boundary else None
        total = Metrics()
        employees = {member.user_id: Metrics() for member in members}
        events, incoming = defaultdict(list), defaultdict(list)
        # All earlier facts are necessary to establish intervals crossing from.
        for event in ConversationEvent.objects.filter(
            organization_id=context.organization_id, conversation_id__in=conversations.values("pk"),
            occurred_at__lte=now,
        ).order_by("conversation_id", "sequence").iterator():
            events[event.conversation_id].append(event)
        for message in Message.objects.filter(
            organization_id=context.organization_id, conversation_id__in=conversations.values("pk"),
            author_type="CONTACT", created_at__lt=upper,
        ).only("pk", "created_at", "conversation_id").order_by("conversation_id", "created_at", "pk").iterator():
            incoming[message.conversation_id].append(message)
        incomplete = []
        details = []
        for conversation in conversations.filter(created_at__lt=upper).only("pk", "created_at").iterator():
            facts = events[conversation.pk]
            legacy = available is None or conversation.created_at < available
            # No current dimension is used to pretend historical coverage.
            relevant = legacy or any(filters.matches(event, employee=event.responsible_id)
                                     or filters.matches(event, employee=event.initiated_by_id) for event in facts)
            if legacy and relevant:
                incomplete.append(conversation.pk)
            for observation in conversation_observations(facts, incoming[conversation.pk], upper):
                detail = total.add(observation, conversation.pk, filters)
                if detail:
                    if detail["employee"] not in employees:
                        detail["employee"] = None
                    details.append(detail)
                metric = employees.get(observation.employee)
                if metric:
                    metric.add(observation, conversation.pk, filters, employee=observation.employee)
        # Earlier demo shifts have their own events and do not create live inbox items.
        for case, observation in weekly_report_observations(context, conversations, filters, upper):
            total.add(observation, case, filters)
            metric = employees.get(observation.employee)
            if metric:
                metric.add(observation, case, filters, employee=observation.employee)
        complete = available is not None and filters.start >= available and not incomplete
        # Counters need no pre-period state, unlike intervals on legacy dialogs.
        counters_complete = available is not None and filters.start >= available
        load = _load(conversations, filters)
        waiting = _load(conversations, filters, waiting=True)
        status_rows, status_totals, status_details = team_status_report(
            organization_id=context.organization_id, members=members, filters=filters, upper=upper,
            tracking_from=boundary.status_stops_available_from if boundary else upper,
        )
        rows = []
        feedback, employee_feedback = report_feedback(
            context=context, conversations=conversations, members=members, filters=filters, now=now,
        )
        for member in members:
            rows.append({"employee": member.user_id, "name": member.user.full_name,
                         "blocked": member.blocked_at is not None, "active": member.user.is_active,
                         "metrics": employees[member.user_id].payload(
                             complete, counters_complete=counters_complete, include_observed=True),
                         "workStatuses": status_rows[member.user_id],
                         **employee_feedback[member.user_id],
                         "currentLoad": load.get(member.user_id, 0),
                         "waitingReplies": waiting.get(member.user_id, 0)})
        return {"period": filters.payload(), "generatedAt": now.isoformat(),
                "durationUnit": "seconds", "countUnit": "conversations_or_events",
                "coverage": {"availableFrom": available.isoformat() if available else None,
                             "storageAvailableFrom": boundary.available_from.isoformat() if boundary else None,
                             "statusStopsAvailableFrom": boundary.status_stops_available_from.isoformat() if boundary else None,
                             "complete": complete, "incompleteConversationIds": incomplete,
                             "reason": None if complete else "missing_history"},
                "totals": total.payload(complete, counters_complete=counters_complete, include_observed=True),
                "employees": rows, **feedback,
                "workStatusTotals": status_totals, "workStatusDetails": status_details,
                "currentLoad": sum(load.values()), "details": details}
