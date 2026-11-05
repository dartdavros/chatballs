"""Call lifecycle data, without signaling or issued access credentials."""

from dataclasses import replace

from chatballs.calls.models import (
    CallConnectionType,
    CallEndedBy,
    CallKind,
    CallStatus,
    ParticipantConnectionState,
    ParticipantSide,
)
from chatballs.integrations.action_catalog.schema import enum, labelled_codes, obj
from chatballs.integrations.adapters.schema import TypeSpec

TEXT = TypeSpec("string")
INTEGER = TypeSpec("integer", nullable=True)
DATE = TypeSpec("datetime", nullable=True)
KIND = replace(enum(CallKind.values, "native.call_kind"), title_key="native.call_type")
STATUS = replace(enum(CallStatus.values, "native.call_status"), title_key="native.call_lifecycle")
SIDE = enum(ParticipantSide.values, "native.call_side")
ENDED_BY = replace(enum(CallEndedBy.values, "native.call_ended_by"), nullable=True)
CALL_ID = TypeSpec("string", required=True, pattern=r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",
    title_key="native.call_id")
PARTICIPANT = obj(side=SIDE, connectionState=enum(ParticipantConnectionState.values, "native.call_connection_state"),
    joinedAt=DATE, leftAt=DATE)
METRIC = obj(side=SIDE, connectionType=enum(CallConnectionType.values, "native.call_connection_type"),
    localCandidateType=labelled_codes(("host", "srflx", "prflx", "relay"), "native.call_candidate",
        "native.call_candidate_unknown", nullable=True),
    remoteCandidateType=labelled_codes(("host", "srflx", "prflx", "relay"), "native.call_candidate",
        "native.call_candidate_unknown", nullable=True),
    roundTripMs=TypeSpec("number", nullable=True))
CALL = obj(id=TEXT, conversationId=INTEGER, status=STATUS, kind=KIND,
    initiatedByUserId=INTEGER, deliveryConnectionId=INTEGER, requestedAt=DATE, acceptedAt=DATE,
    connectedAt=DATE, endedAt=DATE, endedBy=ENDED_BY,
    failureCode=labelled_codes(("ABORTED_BEFORE_CONNECT",), "native.call_failure",
        "native.call_failure_unknown", nullable=True),
    durationSeconds=INTEGER, participants=TypeSpec("array", items=PARTICIPANT), metrics=TypeSpec("array", items=METRIC))
CALL_RESULT = obj(call=CALL)
ACTIVE_RESULT = obj(call=replace(CALL, nullable=True))
PUBLIC_CALL = obj(callId=TEXT, status=STATUS, kind=KIND, staffName=TEXT, endedBy=ENDED_BY, durationSeconds=INTEGER)
