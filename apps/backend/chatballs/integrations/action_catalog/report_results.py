"""Typed selectors and aggregate outputs for the common result journal."""

from dataclasses import replace

from chatballs.conversations.domain_event_models import ConversationEventTransport
from chatballs.conversations.support_metrics import DURATIONS
from chatballs.identity.work_status_codes import WorkStatus
from chatballs.integrations.action_catalog.feedback_schemas import FEEDBACK
from chatballs.integrations.action_catalog.metric_schemas import DURATION, METRICS, NUMBER
from chatballs.integrations.action_catalog.report_schemas import INTEGER, PERIOD
from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, enum, obj
from chatballs.integrations.adapters.schema import TypeSpec

DATE = TypeSpec("datetime", nullable=True)
IDENTITY = obj(id=INTEGER, name=TEXT)
OVERVIEW = obj(waiting=INTEGER, ops=obj(openDialogs=INTEGER, activeNow=INTEGER, onAI=INTEGER,
    onOperators=INTEGER, waiting=INTEGER), period=obj(dialogs=INTEGER, dialogsPrev=INTEGER, messages=INTEGER),
    byChannel=TypeSpec("array", items=obj(code=TEXT, name=TEXT, openDialogs=INTEGER, dialogs=INTEGER)),
    chart=obj(values=TypeSpec("array", items=INTEGER), labels=TypeSpec("array", items=TEXT)),
    problems=TypeSpec("array", items=obj(conversationId=INTEGER, title=TEXT, meta=TEXT, minutes=INTEGER)))
ACCESS = obj(actions=TypeSpec("array", items=enum(("reports.view", "reports.export"), "native.report_action")),
    restricted=BOOLEAN, revokedAt=DATE, groups=TypeSpec("array", items=IDENTITY),
    employees=TypeSpec("array", items=replace(obj(id=INTEGER, fullName=TEXT, email=TEXT,
        isBlocked=BOOLEAN, avatarUrl=TypeSpec("string", nullable=True)), open=True)),
    connections=TypeSpec("array", items=replace(obj(id=INTEGER, name=TEXT, provider=enum(ConversationEventTransport.values, "native.report_transport")), open=True)),
    timezone=TEXT, timezones=TypeSpec("array", items=TEXT))
STATUS_VALUES = obj(**{status: DURATION for status in WorkStatus.values})
WORK_STATUSES = replace(obj(complete=BOOLEAN, availableFrom=DATE, included=BOOLEAN, blockedAt=DATE, values=STATUS_VALUES), open=True)
COVERAGE = obj(complete=BOOLEAN, availableFrom=DATE, storageAvailableFrom=DATE, statusStopsAvailableFrom=DATE,
    incompleteConversationIds=TypeSpec("array", items=INTEGER),
    reason=replace(enum(("missing_history",), "native.report_coverage_reason"), nullable=True))
SUPPORT = replace(obj(period=PERIOD, generatedAt=TypeSpec("datetime"), coverage=COVERAGE, totals=METRICS,
    employees=TypeSpec("array", items=replace(obj(employee=INTEGER, name=TEXT, blocked=BOOLEAN, active=BOOLEAN,
        metrics=METRICS, currentLoad=INTEGER, waitingReplies=INTEGER, workStatuses=WORK_STATUSES, **FEEDBACK), open=True)),
    workStatusTotals=replace(obj(complete=BOOLEAN, employees=INTEGER, values=STATUS_VALUES), open=True),
    workStatusDetails=TypeSpec("array", items=replace(obj(employee=INTEGER,
        status=enum(WorkStatus.values, "native.fields"), version=INTEGER,
        **{"from": TypeSpec("datetime"), "to": TypeSpec("datetime")}, seconds=NUMBER, current=BOOLEAN), open=True)),
    currentLoad=INTEGER, details=TypeSpec("array", items=obj(conversationId=INTEGER,
        metric=enum(DURATIONS, "native.metric"),
        employee=replace(INTEGER, nullable=True), group=replace(INTEGER, nullable=True),
        connection=replace(INTEGER, nullable=True),
        transport=replace(enum(ConversationEventTransport.values, "native.report_transport"), nullable=True),
        **{"from": TypeSpec("datetime"), "to": TypeSpec("datetime")}, seconds=NUMBER, current=BOOLEAN)),
    durationUnit=enum(("seconds",), "native.report_unit"),
    countUnit=enum(("conversations_or_events",), "native.report_unit"), **FEEDBACK), open=True)
