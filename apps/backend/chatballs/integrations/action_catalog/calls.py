"""Call actions preserve staff visibility and original token side/subject rules."""

import json
from functools import partial

from chatballs.calls import operations, public_access
from chatballs.calls.serializers import call_payload, public_call_state_payload
from chatballs.integrations.action_catalog.call_schemas import (
    ACTIVE_RESULT,
    CALL_ID,
    CALL_RESULT,
    KIND,
    PUBLIC_CALL,
)
from chatballs.integrations.action_catalog.contracts import APIEntry
from chatballs.integrations.action_catalog.schema import CONVERSATION_ID, action, obj, required
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def completed(data):
    # Source serializers may contain fresh Django TextChoices instances; their
    # wire representation is a string, as in the original JSON API.
    return OperationResult(ResultState.COMPLETED, json.loads(json.dumps(data)))


def create(context, values):
    context.require_conversation(values["conversation_id"])
    _created, call = operations.create(context.tenant, values["conversation_id"], values["kind"])
    return completed({"call": call_payload(call)})


def active(context, values):
    context.require_conversation(values["conversation_id"])
    call = operations.active(context.tenant, values["conversation_id"])
    return completed({"call": call_payload(call) if call else None})


def session(context, values, *, cancel=False):
    call = operations.detail(context.tenant, values["call_session_id"])
    context.require_conversation(call.conversation_id)
    if cancel:
        call = operations.cancel(context.tenant, call.id)
    return completed({"call": call_payload(call)})


def by_credential(context, values, *, service):
    _claims, call, _tenant = public_access.authorize_call_access_context(
        token=values["credential"], allow_terminal=True,
        expected_organization_id=context.tenant.organization_id,
    )
    context.require_conversation(call.conversation_id)
    call = service(token=values["credential"])
    return completed({"call": public_call_state_payload(call)})


for key, title, inputs, output, handler, route, view, method, capability, scope in (
    ("invite.post", "native.call_create", obj(conversation_id=CONVERSATION_ID, kind=required(KIND)), CALL_RESULT, create,
        "calls/conversations/<int:conversation_id>/", "CallCreateView", "POST", "conversations.call", "conversation"),
    ("active.get", "native.call_active", obj(conversation_id=CONVERSATION_ID), ACTIVE_RESULT, active,
        "calls/conversations/<int:conversation_id>/active/", "ConversationActiveCallView", "GET", "conversations.call", "conversation"),
    ("session.get", "native.call_detail", obj(call_session_id=CALL_ID), CALL_RESULT, session,
        "calls/<uuid:call_session_id>/", "CallDetailView", "GET", "conversations.call", "conversation"),
    ("cancel.post", "native.call_cancel", obj(call_session_id=CALL_ID), CALL_RESULT, partial(session, cancel=True),
        "calls/<uuid:call_session_id>/cancel/", "CallCancelView", "POST", "conversations.call", "conversation"),
):
    action(key=f"calls.{key}", title=title, input=inputs, output=output, handler=handler,
        capability=capability, scope=scope, route=route, view=f"chatballs.calls.views.{view}", method=method)

for key, title, handler, view in (
    ("state", "native.call_state", public_access.call_state_by_access_token, "CallAccessStateView"),
    ("accept", "native.call_accept", public_access.accept_call_by_access_token, "CallAccessAcceptView"),
    ("decline", "native.call_decline", public_access.decline_call_by_access_token, "CallAccessDeclineView"),
    ("end", "native.call_end", public_access.end_call_by_access_token, "CallAccessEndView"),
):
    action(key=f"calls.{key}.post", title=title,
        input=obj(credential=TypeSpec("string", required=True, secret=True, title_key="native.call_credential")),
        output=obj(call=PUBLIC_CALL), handler=partial(by_credential, service=handler), capability="", scope="conversation",
        route=f"api/v1/calls/access/{key}/", view=f"chatballs.calls.views.{view}", method="POST",
        extra_entries=(APIEntry("ws/calls/", "WS:call.ended",
            "chatballs.calls.consumers.CallSignalingConsumer"),) if key == "end" else (),
        effect=Effect.READ if key == "state" else Effect.UPDATE)
