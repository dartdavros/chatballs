"""Typed rule settings and journal, using original domain enumeration values."""

from dataclasses import replace

from chatballs.conversations.domain_event_models import ConversationEventType
from chatballs.conversations.queue_models import QueueEscalationPolicy
from chatballs.conversations.rules.models import (
    HandlingRuleKind,
    RuleAction,
    RuleExecutionReason,
    RuleExecutionStatus,
    RuleRecipient,
)
from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, enum, obj
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

KIND = enum(HandlingRuleKind.values, "native.rule_kind")
STATUS = enum(RuleExecutionStatus.values, "native.rule_status")
RECIPIENT = enum(RuleRecipient.values, "native.rule_recipient")
CONDITIONS = obj(channelIds=TypeSpec("array", items=TypeSpec("integer")), availableOnly=BOOLEAN)
RULE_CHANGES = {"enabled": BOOLEAN, "delayMinutes": TypeSpec("integer", nullable=True),
    "conditions": CONDITIONS, "recipients": TypeSpec("array", items=RECIPIENT),
    "text": TypeSpec("string", max_length=1000)}
RULE = obj(kind=KIND, version=TypeSpec("integer"), **RULE_CHANGES,
    updatedAt=TypeSpec("datetime", nullable=True), updatedBy=TEXT, catalog=obj(
        conditions=TypeSpec("array", items=enum(("channelIds", "availableOnly"), "native.rule_condition")),
        recipients=TypeSpec("array", items=RECIPIENT), requiresText=BOOLEAN, maxDelayMinutes=TypeSpec("integer"),
        maxTextLength=TypeSpec("integer"), deadlinePlaceholder=TEXT))
# Existing reason labels use an underscore namespace.
REASON = TypeSpec("enum", options=tuple(EnumOption(value, f"rules.reason_{value}")
    for value in RuleExecutionReason.values) + (EnumOption("", "native.rule_no_reason"),))
EXECUTION = obj(id=TypeSpec("integer"), rule=obj(kind=KIND, version=TypeSpec("integer")),
    action=enum(RuleAction.values, "native.rule_action"), conversationId=TypeSpec("integer"),
    sourceEvent=obj(id=TypeSpec("integer"), type=replace(enum(ConversationEventType.values, "native.event_type"), title_key="native.event_type_label"),
        occurredAt=TypeSpec("datetime", nullable=True)), startedAt=TypeSpec("datetime", nullable=True),
    scheduledFor=TypeSpec("datetime", nullable=True), finishedAt=TypeSpec("datetime", nullable=True),
    status=STATUS, reason=REASON, reasonLabel=TEXT, attempts=TypeSpec("integer"),
    messageId=TypeSpec("integer", nullable=True), notificationId=TypeSpec("integer", nullable=True),
    recipients=TypeSpec("array", items=obj(userId=TypeSpec("integer"), name=TEXT)))
QUEUE_FIELDS = {key: TypeSpec("integer") for key in QueueEscalationPolicy.DEFAULTS}
QUEUE = obj(**QUEUE_FIELDS, defaults=obj(**QUEUE_FIELDS), updatedAt=TypeSpec("datetime", nullable=True), updatedBy=TEXT)
