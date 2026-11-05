"""Typed assignment policy and protected transfer history outputs."""

from dataclasses import replace

from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, obj, required
from chatballs.integrations.adapters.schema import TypeSpec

REASON_OPTION = obj(id=TypeSpec("integer"), code=TEXT, name=TEXT, isActive=BOOLEAN)
REASON = replace(REASON_OPTION, properties=REASON_OPTION.properties + obj(
    usageCount=TypeSpec("integer"), previousName=TEXT, renamedAt=TypeSpec("datetime", nullable=True)).properties)
POLICY_INPUT = obj(**{key: required(BOOLEAN) for key in ("READY", "BUSY", "BREAK", "UNAVAILABLE")})
POLICY_RESULT = obj(allowedStatuses=replace(POLICY_INPUT, nullable=True))
PERSON = replace(obj(id=TypeSpec("integer"), name=TEXT, avatarUrl=TypeSpec("string", nullable=True)), nullable=True)
TRANSFER = obj(id=TypeSpec("integer"), conversationId=TypeSpec("integer"), operationId=TEXT,
    assignmentVersion=TypeSpec("integer"), initiatedById=TypeSpec("integer", nullable=True),
    previousOperatorId=TypeSpec("integer", nullable=True), newOperatorId=TypeSpec("integer", nullable=True),
    occurredAt=TypeSpec("datetime"), reason=obj(id=TypeSpec("integer"), code=TEXT, name=TEXT), comment=TEXT)
HISTORY_TRANSFER = replace(TRANSFER, properties=tuple((name, replace(field, properties=field.properties + obj(
    isActive=BOOLEAN, currentName=TEXT).properties) if name == "reason" else field)
    for name, field in TRANSFER.properties) + obj(initiatedBy=PERSON, previousOperator=PERSON,
        newOperator=PERSON, conversation=obj(contactName=TEXT, provider=TEXT)).properties)
