"""Client message facts share their domain transaction; no message text in outbox."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from chatballs.conversations.models import Message
from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.adapters.events import VerifiedEvent
from chatballs.integrations.automation_events.ingress import persist
from chatballs.tenancy.context import TenantContext


@receiver(post_save, sender=Message, dispatch_uid="scenario-client-reply")
def client_reply(sender, instance, created, **kwargs):
    if not created or instance.author_type != "CONTACT":
        return
    tenant = TenantContext.for_resource(instance.conversation.organization)
    enqueue_event(DomainEvent(aggregate_type="scenario_reply", aggregate_id=str(instance.pk),
        event_type="integrations.reply", payload={"messageId": instance.pk}, tenant_context=tenant))


@register("integrations.reply")
def accept_reply(payload, tenant):
    message = Message.objects.select_related("conversation").filter(
        pk=payload["messageId"], conversation__organization_id=tenant.organization_id, author_type="CONTACT").first()
    if message is None:
        return
    persist(tenant, None, VerifiedEvent(event_id=f"reply:{message.pk}", event_key="conversation.reply",
        occurred_at=message.created_at, payload={"conversationId": message.conversation_id}), replay_seconds=30 * 86400)
