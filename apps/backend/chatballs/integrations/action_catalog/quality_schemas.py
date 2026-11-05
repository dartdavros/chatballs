"""Quality criteria, immutable job snapshots and append-only reviews."""

from dataclasses import replace

from chatballs.conversations.quality.models import QualityJobState
from chatballs.integrations.action_catalog.metric_schemas import METRICS
from chatballs.integrations.action_catalog.report_schemas import INTEGER
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    TEXT,
    enum,
    labelled_codes,
    obj,
    required,
)
from chatballs.integrations.adapters.schema import TypeSpec

VALUE = obj(textValue=TEXT, integerValue=INTEGER, numberValue=TypeSpec("number"))
ERROR = labelled_codes(("analysis_interrupted", "provider_unavailable", "invalid_result"),
    "native.quality_error", "native.quality_error_unknown", nullable=True)
MISSING = labelled_codes(("insufficient_messages",), "native.quality_missing",
    "native.quality_missing_unknown", nullable=True)
CRITERION = obj(code=required(replace(TEXT, pattern=r"[a-zA-Z0-9_-]{1,64}")),
    name=replace(TEXT, max_length=200), description=required(TEXT),
    scale=required(TypeSpec("array", items=VALUE, min_items=1)), reporting=obj(positiveValue=required(TEXT)))
CRITERIA = TypeSpec("array", items=CRITERION)
SETTINGS = obj(enabled=BOOLEAN, criteriaVersion=replace(INTEGER, nullable=True), nextCriteriaVersion=INTEGER,
    criteriaCreatedAt=TypeSpec("datetime", nullable=True), criteria=CRITERIA,
    suggestedCriteria=replace(CRITERIA, nullable=True),
    scales=TypeSpec("array", items=obj(id=TEXT, label=TEXT, values=TypeSpec("array", items=VALUE))),
    criteriaValueLiterals=TypeSpec("object", open=True))
AUTHOR = replace(obj(membershipId=INTEGER, userId=INTEGER, name=TEXT), nullable=True)
CONCLUSION = obj(code=TEXT, originalValue=replace(VALUE, nullable=True), effectiveValue=replace(VALUE, nullable=True),
    effectiveScaleIndex=replace(INTEGER, nullable=True), missingReason=MISSING, explanation=TEXT,
    recommendations=TypeSpec("array", items=TEXT), evidence=TypeSpec("array", items=obj(messageId=INTEGER, url=TEXT)),
    evidenceAvailable=BOOLEAN)
CORRECTION = obj(revision=INTEGER, criterionCode=TEXT, value=VALUE, author=AUTHOR, createdAt=TypeSpec("datetime"), reason=TEXT)
JOB = obj(id=INTEGER, conversationId=INTEGER, completionEventId=TEXT, completedAt=TypeSpec("datetime"),
    revision=INTEGER, historyRevision=TEXT, criteriaVersion=INTEGER, criteria=CRITERIA,
    state=enum(QualityJobState.values, "native.quality_state"), errorCode=ERROR,
    startedAt=TypeSpec("datetime", nullable=True), finishedAt=TypeSpec("datetime", nullable=True),
    resultId=replace(INTEGER, nullable=True), temporalFacts=replace(obj(
        state=enum(("available", "missing_history"), "native.temporal_state"),
        unit=enum(("seconds",), "native.report_unit"),
        availableFrom=TypeSpec("datetime", nullable=True), metrics=METRICS), open=True, nullable=True),
    conclusions=TypeSpec("array", items=CONCLUSION), correctionRevision=INTEGER,
    corrections=TypeSpec("array", items=CORRECTION))
JOBS = TypeSpec("array", items=JOB)
