"""Complete support-feedback results, retaining independent scales/versions."""

from dataclasses import replace

from chatballs.conversations.domain_event_models import ConversationEventTransport
from chatballs.conversations.quality.models import QualityJobState
from chatballs.integrations.action_catalog.quality_schemas import ERROR, MISSING, VALUE
from chatballs.integrations.action_catalog.rating_schemas import GROUP, PROTECTED, SCALE, SCORE
from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, enum, obj
from chatballs.integrations.adapters.schema import TypeSpec

INTEGER = TypeSpec("integer")
COUNT = replace(INTEGER, nullable=True)
RATE = TypeSpec("number", nullable=True)
DATE = TypeSpec("datetime")
VALUES = TypeSpec("array", items=VALUE)
AVAILABILITY = enum(("available", "forbidden"), "native.feedback_state")
BASIS = enum(("received_at", "sent_at", "completed_at"), "native.feedback_basis")
DIMENSIONS = dict(group=COUNT, connection=COUNT,
    transport=replace(enum(ConversationEventTransport.values, "native.report_transport"), nullable=True))
RATING_DETAIL = replace(PROTECTED, properties=PROTECTED.properties + obj(**DIMENSIONS).properties)
RATING_SUMMARY = obj(scaleId=TEXT, scale=SCALE, ratingCount=INTEGER, meanValue=RATE,
    commentCount=INTEGER, periodBasis=BASIS,
    distribution=TypeSpec("array", items=obj(value=SCORE, label=TEXT, count=INTEGER, rate=RATE)),
    delivery=obj(periodBasis=BASIS, answeredBefore=DATE, sentCount=INTEGER,
        answeredCount=INTEGER, responseRate=RATE))
RATINGS = obj(state=AVAILABILITY, periodBasis=BASIS, count=COUNT,
    groups=TypeSpec("array", items=GROUP), details=TypeSpec("array", items=RATING_DETAIL),
    scaleSummaries=TypeSpec("array", items=RATING_SUMMARY))
CONCLUSION = obj(code=TEXT, scale=VALUES, originalValue=replace(VALUE, nullable=True),
    effectiveValue=replace(VALUE, nullable=True), corrected=BOOLEAN,
    missingReason=MISSING)
QUALITY_DETAIL = obj(id=INTEGER, conversationId=INTEGER, completionEventId=TEXT,
    completedAt=DATE, revision=INTEGER, historyRevision=TEXT, criteriaVersionId=INTEGER,
    criteriaVersion=INTEGER, responderIds=TypeSpec("array", items=INTEGER),
    state=enum(QualityJobState.values, "native.quality_state"), errorCode=ERROR,
    correctionRevision=INTEGER, conclusions=TypeSpec("array", items=CONCLUSION), **DIMENSIONS)
BUCKETS = TypeSpec("array", items=obj(value=VALUE, count=INTEGER))
QUALITY_GROUP = obj(criteriaVersionId=INTEGER, criteriaVersion=INTEGER, code=TEXT, scale=VALUES,
    count=INTEGER, originalValues=BUCKETS, effectiveValues=BUCKETS)
SUMMARY = obj(kind=enum(("positiveRate", "mean", "unavailable"), "native.feedback_summary"),
    positiveValue=VALUE, value=RATE)
VERSION = obj(criteriaVersionId=INTEGER, criteriaVersion=INTEGER, validFrom=DATE,
    validTo=replace(DATE, nullable=True), analysisCount=INTEGER, selectedJobCount=INTEGER,
    correctedAnalysisCount=INTEGER, correctionRate=RATE,
    criteria=TypeSpec("array", items=obj(code=TEXT, name=TEXT, description=TEXT, scale=VALUES,
        scoredCount=COUNT, missingCount=COUNT, correctedCount=COUNT,
        originalSummary=SUMMARY, effectiveSummary=SUMMARY)))
QUALITY = obj(state=AVAILABILITY, periodBasis=BASIS,
    revisionPolicy=enum(("latest_per_completion",), "native.feedback_revision"), count=COUNT,
    states=obj(**{state: replace(INTEGER, title_key=f"native.quality_state.{state}")
        for state in QualityJobState.values}), groups=TypeSpec("array", items=QUALITY_GROUP),
    details=TypeSpec("array", items=QUALITY_DETAIL), versions=TypeSpec("array", items=VERSION))
FEEDBACK = dict(customerRatings=RATINGS, qualityAnalysis=QUALITY)
