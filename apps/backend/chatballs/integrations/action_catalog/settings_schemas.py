"""Explicit organization settings, audit and asynchronous demo-state contracts."""

from dataclasses import replace

from chatballs.identity.audit_catalog import (
    AUDIT_ACTION_LABELS,
    AUDIT_CATEGORY_LABELS,
    AUDIT_OBJECT_TYPE_LABELS,
    AUDIT_RESULT_LABELS,
)
from chatballs.integrations.action_catalog.employee_schemas import ROLE
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import enum, obj
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.settings.{name}", **kwargs)


def codes(name, labels):
    return field(name, options=tuple(EnumOption(value, key) for value, key in labels.items()),
        placeholder_key=f"native.settings.{name}")


MODE = replace(enum(("AI_AGENTS", "OPERATORS_ONLY"), "native.settings.mode"), title_key="native.settings.operationMode")
EDIT = dict(name=field("name"), timezone=field("timezone"), language=field("language"), operationMode=MODE)
ORGANIZATION = field("organization", "object", properties=obj(**EDIT,
    operationModeVersion=field("operationModeVersion", "integer"),
    updatedAt=field("updatedAt", "datetime", nullable=True), logoUrl=field("logoUrl", nullable=True)).properties)
OUTPUT = obj(organization=ORGANIZATION)
READ = obj(organization=ORGANIZATION, timezones=field("timezones", "array", items=TypeSpec("string")),
    languages=field("languages", "array", items=obj(code=field("language"), label=field("label"))))
ONBOARDING = obj(operationMode=MODE,
    dismissedAt=field("dismissedAt", "datetime", nullable=True), completedAt=field("completedAt", "datetime", nullable=True),
    steps=field("steps", "object", properties=tuple((key, field(key, "boolean")) for key in (
        "providerConnected", "agentActive", "knowledgeFilled", "connectionBound", "widgetPublished",
        "employeeInvited", "platformConfigured", "firstConversation"))))
ONBOARDING_INPUT = obj(action=replace(enum(("dismiss", "complete", "restart"), "native.settings.onboarding"), title_key="native.settings.action"))
COMMUNICATION_FIELDS = {key: field(key, "boolean") for key in ("voiceMessages", "audioCalls", "videoCalls")}
COMMUNICATION_INPUT = obj(items=TypeSpec("array", required=True, items=obj(
    id=TypeSpec("integer", required=True), **COMMUNICATION_FIELDS)))
COMMUNICATION = obj(items=TypeSpec("array", items=obj(id=TypeSpec("integer"), name=field("connectionName"),
    provider=replace(enum(("MAX", "TELEGRAM", "VK", "WEB", "EMAIL"), "native.report_transport"), title_key="native.settings.provider"),
    isActive=field("isActive", "boolean"), agentName=field("agentName"), supportsCalls=field("supportsCalls", "boolean"),
    **COMMUNICATION_FIELDS)))
FILTER = obj(value=field("value"), label=field("label"))
AUDIT_ITEM = obj(id=TypeSpec("integer"), createdAt=field("createdAt", "datetime"),
    actorId=field("actorId", "integer", nullable=True), actor=field("actor"), actorEmail=field("actorEmail"),
    action=codes("action", AUDIT_ACTION_LABELS), actionLabel=field("action"),
    category=codes("category", AUDIT_CATEGORY_LABELS), categoryLabel=field("category"),
    object=field("object"), objectType=codes("objectType", AUDIT_OBJECT_TYPE_LABELS), objectId=field("objectId"),
    result=codes("result", AUDIT_RESULT_LABELS), resultLabel=field("result"),
    sourceIp=field("sourceIp"), correlationId=field("correlationId"), details=field("details", "object", open=True))
AUDIT = replace(page_of(AUDIT_ITEM), properties=page_of(AUDIT_ITEM).properties + (
    ("filters", field("filters", "object", properties=tuple((key, field(key, "array", items=FILTER))
        for key in ("categories", "results", "actors")))),))
AUDIT_INPUT = obj(**PAGE_INPUTS, period=replace(enum(("today", "7d", "30d", "90d"), "native.settings.period"), title_key="native.settings.period"),
    category=codes("category", AUDIT_CATEGORY_LABELS), result=codes("result", AUDIT_RESULT_LABELS),
    actor=field("actorId"), q=field("search"))
DEMO_ACCOUNT = obj(fullName=field("fullName"), email=field("email"), role=ROLE, positionTitle=field("positionTitle"),
    groups=field("groups", "array", items=TypeSpec("string")), avatarUrl=field("avatarUrl", nullable=True))
DEMO = obj(status=replace(enum(("ABSENT", "INSTALLING", "INSTALLED", "REMOVING", "FAILED"), "native.settings.demo_status"), title_key="native.settings.status"),
    recordsCount=field("recordsCount", "integer"), error=field("error"),
    startedAt=field("startedAt", "datetime", nullable=True), finishedAt=field("finishedAt", "datetime", nullable=True),
    accounts=field("accounts", "array", items=DEMO_ACCOUNT))
