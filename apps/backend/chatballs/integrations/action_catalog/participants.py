"""Participant actions retain source composition checks and audit."""

from dataclasses import replace

from chatballs.conversations.participant_payloads import participant_payload
from chatballs.conversations.participant_queries import active_participants, participant_history
from chatballs.conversations.participant_services import add_participant, remove_participant
from chatballs.conversations.participant_settings import participant_limit
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    IDENTIFIER,
    TEXT,
    action,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

PERSON = replace(obj(membershipId=TypeSpec("integer"), userId=TypeSpec("integer"),
    name=TEXT, avatarUrl=TypeSpec("string", nullable=True)), nullable=True)
PARTICIPANT = obj(id=TypeSpec("integer"), membershipId=TypeSpec("integer"), userId=TypeSpec("integer"),
    member=PERSON, joinedBy=PERSON, leftBy=PERSON, joinedByMembershipId=TypeSpec("integer", nullable=True),
    joinedAt=TypeSpec("datetime"), joinReason=TEXT, leftByMembershipId=TypeSpec("integer", nullable=True),
    leftAt=TypeSpec("datetime", nullable=True), leaveReason=TEXT)
ACTIVE_PARTICIPANT = replace(PARTICIPANT, properties=PARTICIPANT.properties + obj(
    workStatus=obj(status=TEXT, version=TypeSpec("integer"), changedAt=TypeSpec("datetime", nullable=True)),
    online=BOOLEAN, lastSeenAt=TypeSpec("datetime", nullable=True)).properties)
LIMIT = obj(additionalParticipantLimit=TypeSpec("integer"), updatedAt=TypeSpec("datetime", nullable=True), updatedBy=TEXT)


def result(value):
    return OperationResult(ResultState.COMPLETED, value)


def listing(context, values):
    return result(active_participants(context.tenant, values["conversation_id"]))


def history(context, values):
    return result(participant_history(context.tenant, values["conversation_id"], values))


def add(context, values):
    row, _ = add_participant(context=context.tenant, conversation_id=values["conversation_id"],
        membership_id=values["membership_id"], reason=values["reason"])
    return result({"participant": participant_payload(row)})


def remove(context, values):
    row, _ = remove_participant(context=context.tenant, conversation_id=values["conversation_id"],
        participant_id=values["participant_id"], reason=values["reason"])
    return result({"participant": participant_payload(row)})


def limit(context, values):
    return result(participant_limit(context.tenant))


def update_limit(context, values):
    return result(participant_limit(context.tenant, values))


for key, title, inputs, output, handler, method, route, view, capability, scope in (
    ("participants.get", "native.participants_list", obj(conversation_id=CONVERSATION_ID),
        obj(items=TypeSpec("array", items=ACTIVE_PARTICIPANT), additionalParticipantLimit=TypeSpec("integer")),
        listing, "GET", "<int:conversation_id>/participants/", "ParticipantListView", "conversations.view", "conversation"),
    ("participants.post", "native.participants_add", obj(conversation_id=CONVERSATION_ID,
        membership_id=IDENTIFIER, reason=required(TEXT)), obj(participant=PARTICIPANT),
        add, "POST", "<int:conversation_id>/participants/", "ParticipantListView", "conversations.participants", "conversation"),
    ("participants.member.delete", "native.participants_remove", obj(conversation_id=CONVERSATION_ID,
        participant_id=IDENTIFIER, reason=required(TEXT)), obj(participant=PARTICIPANT), remove, "DELETE",
        "<int:conversation_id>/participants/<int:participant_id>/", "ParticipantDetailView", "conversations.participants", "conversation"),
    ("participants.history.get", "native.participants_history", obj(conversation_id=CONVERSATION_ID, **PAGE_INPUTS),
        page_of(PARTICIPANT), history, "GET", "<int:conversation_id>/participants/history/", "ParticipantHistoryView", "conversations.view", "conversation"),
    ("participants.limit.get", "native.participants_limit", obj(), LIMIT, limit,
        "GET", "participant-limit/", "ParticipantLimitView", "conversations.view", "organization"),
    ("participants.limit.patch", "native.participants_limit_update", obj(additionalParticipantLimit=required(TypeSpec("integer"))),
        LIMIT, update_limit, "PATCH", "participant-limit/", "ParticipantLimitView", "settings.manage", "organization"),
):
    action(key=key, title=title, input=inputs, output=output, handler=handler, method=method,
        route=f"conversations/{route}", view=f"chatballs.conversations.participant_views.{view}",
        capability=capability, scope=scope)
