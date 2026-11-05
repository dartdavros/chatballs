"""A durable audience and independent delivery transactions for every subscriber."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.execution.automation import launch_automatic
from chatballs.integrations.execution.events import system_context
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.automation import EventDelivery, EventSubscription
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.tenancy.database import tenant_atomic


def schedule(tenant, receipt, *, after=0):
    enqueue_event(DomainEvent(aggregate_type="scenario_fanout", aggregate_id=str(receipt.pk),
        event_type="integrations.fanout", payload={"receiptId": receipt.pk, "after": after},
        tenant_context=system_context(tenant)))


def seed(tenant, receipt, *, scenario_id=None):
    # Store audience before ACK: later subscriptions cannot consume an old event.
    subscriptions = EventSubscription.objects.filter(organization_id=receipt.organization_id, active=True,
        integration_id=receipt.integration_id, event_key=receipt.event_key)
    if scenario_id is not None:
        subscriptions = subscriptions.filter(scenario_id=scenario_id)
    subscriptions = subscriptions.order_by("scenario_id", "pk").values_list(
            "scenario_id", "scenario__public_id", "trigger_id").iterator(chunk_size=500)
    seen, batch = set(), []
    for scenario_id, public_id, trigger_id in subscriptions:
        if scenario_id in seen:
            continue
        seen.add(scenario_id)
        batch.append(EventDelivery(organization_id=receipt.organization_id, receipt=receipt,
            scenario_key=str(public_id), scenario_id=scenario_id, trigger_id=trigger_id))
        if len(batch) == 500:
            EventDelivery.objects.bulk_create(batch)
            batch = []
    EventDelivery.objects.bulk_create(batch)
    if receipt.deliveries.exists():
        schedule(tenant, receipt)


def deliver_one(tenant, pk, *, registry=None):
    with tenant_atomic(tenant):
        identity = EventDelivery.objects.filter(pk=pk, organization_id=tenant.organization_id).values_list("scenario_id", flat=True).first()
        if identity:
            ScenarioDefinition.objects.select_for_update().filter(pk=identity).first()
        row = EventDelivery.objects.select_for_update(of=("self",)).select_related("receipt", "scenario").get(
            pk=pk, organization_id=tenant.organization_id)
        if row.state != "pending":
            return
        if row.error_code and row.due_at > timezone.now():
            return
        try:
            with transaction.atomic():
                if row.scenario is None or not row.scenario.enabled:
                    raise ExecutionDenied("scenario_disabled")
                receipt = row.receipt
                trigger = next((t for t in row.scenario.definition["triggers"] if t["id"] == row.trigger_id), None)
                kind = "service" if receipt.integration_id else "chatballs"
                if (trigger is None or trigger["kind"] != kind or trigger.get("event") != receipt.event_key
                        or kind == "service" and str(trigger.get("connection")) != str(receipt.integration_id)):
                    raise ExecutionDenied("permission")
                if receipt.cleared_at:
                    raise ExecutionDenied("data_cleared")
                event = receipt.definition["payload"]
                # Only native schemas supply a Chatballs conversation ID. External
                # untrusted payload cannot pick a privileged internal context.
                conversation_id = event.get("conversationId") if kind == "chatballs" else None
                if kind == "chatballs" and receipt.event_key == "webchat.site_event":
                    from chatballs.webchat.proactive_launch import prepare
                    conversation_id = prepare(tenant, receipt, row.scenario)
                if kind == "service" and receipt.definition.get("entityKind"):
                    from django.db.models import Q

                    from chatballs.conversations.models import Conversation
                    from chatballs.integrations.scenario_state.entity_links import EntityLink
                    links = EntityLink.objects.filter(organization_id=tenant.organization_id, integration_id=receipt.integration_id,
                        external_kind=receipt.definition["entityKind"], external_id=receipt.definition["entityId"], active=True)
                    ids = list(Conversation.objects.filter(organization_id=tenant.organization_id, archived_at__isnull=True).filter(
                        Q(pk__in=links.filter(internal_kind="conversation").values("internal_id")) |
                        Q(contact_id__in=links.filter(internal_kind="contact").values("internal_id"), lifecycle="OPEN")).values_list("pk", flat=True)[:2])
                    if len(ids) == 1:
                        conversation_id = ids[0]
                row.run, _ = launch_automatic(tenant, row.scenario, trigger,
                    key=f"event:{receipt.source_key}:{receipt.event_id_hash}", event=event,
                    conversation_id=conversation_id, registry=registry, causal_chain=receipt.definition.get("causalChain", []))
                row.state = "delivered"
                row.error_code = ""
        except ExecutionDenied as error:
            row.state = "pending" if str(error) in {"connection_paused", "connection_missing"} else "skipped" if str(error) == "conditions_not_met" else "failed"
            row.error_code = str(error)
            row.due_at = timezone.now() + timedelta(minutes=1)
        row.lease_until = None
        row.save(update_fields=["run", "state", "error_code", "due_at", "lease_until"])


def tick(tenant):
    with tenant_atomic(tenant):
        rows = list(EventDelivery.objects.select_for_update(skip_locked=True).filter(
            organization_id=tenant.organization_id, state="pending", due_at__lte=timezone.now()).filter(
                Q(lease_until__isnull=True) | Q(lease_until__lte=timezone.now())).order_by("due_at", "pk")[:50])
        seen = set()
        for row in rows:
            row.lease_until = timezone.now() + timedelta(seconds=90)
            row.save(update_fields=["lease_until"])
            if row.receipt_id not in seen:
                schedule(tenant, row.receipt)
                seen.add(row.receipt_id)


@register("integrations.fanout", manages_own_transaction=True)
def deliver(payload, tenant):
    with tenant_atomic(tenant):
        receipt = EventReceipt.objects.get(pk=payload["receiptId"], organization_id=tenant.organization_id)
        ids = list(receipt.deliveries.filter(pk__gt=payload.get("after", 0)).order_by("pk").values_list("pk", flat=True)[:50])
    failed = False
    for pk in ids:
        # Unexpected process/database failures retry the outbox. Completed
        # checkpoints survive; expected subscription failures do not stop peers.
        try:
            deliver_one(tenant, pk)
        except Exception:
            failed = True
    if len(ids) == 50:
        with tenant_atomic(tenant):
            schedule(tenant, receipt, after=ids[-1])
    if failed:
        raise RuntimeError("subscriber_delivery_failed")
