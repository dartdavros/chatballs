"""Application operations shared by HTTP and scenario entry points."""

from django.db import transaction

from chatballs.calls.models import CallSession
from chatballs.calls.permissions import ensure_call_access, ensure_conversation_call_access
from chatballs.calls.services import active_call_for_conversation, cancel_call, create_call_request
from chatballs.conversations.models import Conversation
from chatballs.identity.audit import record_audit_event


def call_queryset():
    return CallSession.objects.select_related(
        "conversation", "conversation__channel", "initiated_by", "delivery_connection",
    ).prefetch_related("participants", "metrics")


def detail(context, call_session_id):
    call = call_queryset().get(id=call_session_id, organization=context.organization)
    ensure_call_access(user=context.membership, call_session=call)
    return call


def active(context, conversation_id):
    conversation = Conversation.objects.select_related("channel").get(
        id=conversation_id, organization=context.organization,
    )
    ensure_conversation_call_access(user=context.membership, conversation=conversation)
    return active_call_for_conversation(conversation)


def _audit(context, call, action, *, request=None, payload=None):
    record_audit_event(
        action=f"calls.{action}", actor=context.actor_user, organization=context.organization,
        object_type="CallSession", object_id=str(call.id),
        payload={"conversation_id": call.conversation_id, **(payload or {})}, request=request,
    )


@transaction.atomic
def create(context, conversation_id, kind, *, request=None):
    created = create_call_request(context=context, conversation_id=conversation_id, kind=kind)
    call = call_queryset().get(id=created.call_session.id, organization=context.organization)
    _audit(context, call, "requested", request=request, payload={"kind": call.kind})
    return created, call


@transaction.atomic
def cancel(context, call_session_id, *, request=None):
    call = call_queryset().get(id=call_session_id, organization=context.organization)
    cancel_call(context=context, call_session=call)
    call = call_queryset().get(id=call_session_id, organization=context.organization)
    _audit(context, call, "cancelled", request=request)
    return call
