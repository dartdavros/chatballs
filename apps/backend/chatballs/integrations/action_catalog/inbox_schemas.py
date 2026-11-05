"""Typed inbox, directory, protected activity and visitor observation results."""

from dataclasses import replace

from chatballs.identity.models import EmployeeRole
from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, enum, obj
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.webchat.observation_models import CONNECTION_STATES, PAGE_STATES, WIDGET_STATES

INTEGER = TypeSpec("integer")
DATE = TypeSpec("datetime", nullable=True)
PERSON = replace(obj(id=replace(INTEGER, nullable=True), name=TEXT), nullable=True, open=True)
GROUP = obj(id=INTEGER, name=TEXT, color=TEXT)
COUNTED_GROUP = replace(GROUP, properties=GROUP.properties + obj(count=INTEGER).properties)
NAMED_COUNT = obj(id=INTEGER, name=TEXT, count=INTEGER)
COUNTERS = obj(all=replace(INTEGER, title_key="native.counter_all"), waiting=INTEGER, queue=INTEGER, waitingOnMe=INTEGER,
    assignmentTimeoutMinutes=INTEGER, mine=INTEGER, ungrouped=INTEGER,
    groups=TypeSpec("array", items=COUNTED_GROUP),
    agents=TypeSpec("array", items=replace(NAMED_COUNT, properties=NAMED_COUNT.properties + obj(code=TEXT).properties)),
    assignees=TypeSpec("array", items=replace(NAMED_COUNT, properties=NAMED_COUNT.properties + obj(
        avatarUrl=TypeSpec("string", nullable=True)).properties)))
STATUS = enum(("READY", "BUSY", "BREAK", "UNAVAILABLE"), "native.fields")
POLICY = replace(obj(**{key: BOOLEAN for key in ("READY", "BUSY", "BREAK", "UNAVAILABLE")}), nullable=True)
EMPLOYEE = obj(id=INTEGER, membershipId=INTEGER, name=TEXT, avatarUrl=TypeSpec("string", nullable=True),
    role=enum(EmployeeRole.values, "native.employee_role"), workStatus=obj(status=STATUS, version=INTEGER, changedAt=DATE),
    assignmentAllowed=BOOLEAN, online=BOOLEAN, lastSeenAt=DATE, openDialogs=INTEGER)
DIRECTORY = obj(assignmentAllowedStatuses=POLICY, groups=TypeSpec("array", items=GROUP),
    employees=TypeSpec("array", items=EMPLOYEE), hasMoreEmployees=BOOLEAN)
HISTORY_KIND = replace(enum(("all", "transfers", "participants"), "native.history_filter"), title_key="native.history_kind")
ACTIVITY = obj(id=TEXT, kind=enum(("TRANSFER", "JOIN", "LEAVE", "CLAIM"), "native.activity_kind"),
    occurredAt=TypeSpec("datetime"), actor=PERSON, recipient=PERSON,
    reason=replace(obj(name=TEXT), nullable=True, open=True), comment=TEXT)
JOURNAL = obj(id=TEXT, kind=enum(("JOINED", "LEFT", "TRANSFER"), "native.journal_kind"),
    occurredAt=TypeSpec("datetime"), actorName=TEXT, subjectName=TEXT, reason=TEXT, comment=TEXT,
    reasonChanged=BOOLEAN, reasonInactive=BOOLEAN)
OBSERVATION = obj(tabId=TEXT, sequence=INTEGER, widget=enum(WIDGET_STATES, "native.widget_state"),
    page=replace(enum(PAGE_STATES, "native.page_state"), title_key="native.observation_page"),
    connection=replace(enum(CONNECTION_STATES, "native.connection_state"), title_key="native.observation_connection"),
    departure=enum(("unknown",), "native.departure"), receivedAt=TypeSpec("datetime"),
    heartbeatAt=DATE, widgetChangedAt=DATE, pageChangedAt=DATE, connectionChangedAt=DATE)
VISITORS = obj(sessions=TypeSpec("array", items=obj(heartbeatIntervalSeconds=INTEGER,
    heartbeatTimeoutSeconds=INTEGER, tabs=TypeSpec("array", items=OBSERVATION))))
