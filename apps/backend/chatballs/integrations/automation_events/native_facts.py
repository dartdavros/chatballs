"""Native facts feed existing waits without launching subscribed scenarios."""

from uuid import uuid4

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.models import Conversation
from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.adapters.events import VerifiedEvent
from chatballs.integrations.automation_events.ingress import persist
from chatballs.tenancy.context import TenantContext


def enqueue(conversation, kind, identity, *, occurred_at, tag=None):
    from chatballs.integrations.automation_events.causality import chain
    tenant = TenantContext.for_resource(conversation.organization)
    payload = {"conversationId": conversation.pk, "contactId": conversation.contact_id,
               "event": kind, "identity": identity, "time": occurred_at.isoformat(), "causalChain": list(chain.get())}
    if tag is not None:
        payload["tagId"] = tag
    enqueue_event(DomainEvent(aggregate_type="scenario_native_fact", aggregate_id=identity,
        event_type="integrations.native_fact", payload=payload, tenant_context=tenant))


@receiver(post_save, sender=Conversation, dispatch_uid="scenario-conversation-started")
def started(sender, instance, created, **kwargs):
    if created:
        enqueue(instance, "conversation.started", f"started:{instance.pk}", occurred_at=instance.created_at)


@receiver(post_save, sender=ConversationEvent, dispatch_uid="scenario-conversation-closed")
def closed(sender, instance, created, **kwargs):
    if created and instance.event_type == "CLOSED":
        enqueue(instance.conversation, "conversation.closed", f"closed:{instance.pk}", occurred_at=instance.occurred_at)


@receiver(m2m_changed, sender=Conversation.labels.through, dispatch_uid="scenario-conversation-label-added")
def labelled(sender, instance, action, reverse, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    if reverse:
        conversations = Conversation.objects.filter(pk__in=pk_set, organization_id=instance.organization_id)
        for conversation in conversations:
            enqueue(conversation, "conversation.tag_added", str(uuid4()), occurred_at=timezone.now(), tag=instance.pk)
    else:
        for tag in pk_set:
            enqueue(instance, "conversation.tag_added", str(uuid4()), occurred_at=timezone.now(), tag=tag)


@register("integrations.native_fact")
def deliver_fact(payload, tenant):
    data = {"conversationId": payload["conversationId"], "contactId": payload["contactId"]}
    if "tagId" in payload:
        data["tagId"] = payload["tagId"]
    persist(tenant, None, VerifiedEvent(event_id=payload["identity"], event_key=payload["event"],
        occurred_at=parse_datetime(payload["time"]), payload=data, causal_chain=tuple(payload.get("causalChain", []))), replay_seconds=30 * 86400)
