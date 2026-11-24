"""Tenant-bound system maintenance; human closure retains its own authorization."""

from chatballs.conversations.demo_protection import inactivity_protection_records
from chatballs.conversations.domain_events import operation_key, record_fact
from chatballs.conversations.lifecycle_state import finish_locked
from chatballs.conversations.models import Conversation, LifecycleState
from chatballs.tenancy.context import TenantActorKind


def require_maintenance_context(context):
    if (
        context.actor_kind not in {TenantActorKind.MACHINE, TenantActorKind.SYSTEM}
        or context.actor_user is not None or context.membership is not None
    ):
        raise Conversation.DoesNotExist


def close_inactive_locked(*, context, conversation, cutoff):
    require_maintenance_context(context)
    if conversation.organization_id != context.organization_id:
        raise Conversation.DoesNotExist
    if conversation.lifecycle != LifecycleState.OPEN or conversation.last_activity_at > cutoff:
        return False
    if inactivity_protection_records(
        organization_id=context.organization_id, object_id=str(conversation.pk),
    ).exists():
        return False
    responsible_id = conversation.assigned_operator_id
    was_waiting = conversation.waiting_since is not None
    operation_id = operation_key("auto-close", conversation.pk)
    finish_locked(conversation, LifecycleState.CLOSED)
    if was_waiting:
        record_fact(
            conversation, "QUEUE_EXITED", operation_id=operation_id,
            responsible_id=responsible_id,
        )
    record_fact(
        conversation, "CLOSED", operation_id=operation_id,
        responsible_id=responsible_id,
    )
    return True
