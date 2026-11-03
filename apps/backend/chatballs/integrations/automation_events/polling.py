"""Fenced cursor ingestion with I/O outside transactions and bounded batches."""

import json
import uuid
from dataclasses import replace
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.adapters.contracts import Delivery
from chatballs.integrations.adapters.events import PollResult
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.automation_events.ingress import persist, validate_envelope
from chatballs.integrations.execution.events import system_context
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.automation import PollCursor
from chatballs.integrations.service_connections.binding import build_context, resolve
from chatballs.tenancy.database import tenant_atomic


def discover(tenant):
    registry = default_registry()
    with tenant_atomic(tenant):
        for connection in Integration.objects.filter(organization_id=tenant.organization_id, kind="SERVICE", is_active=True, status="OK").select_related("service_settings"):
            row = getattr(connection, "service_settings", None)
            adapter = registry.adapter(row.adapter_key) if row else None
            if adapter is None or adapter.contract_version != row.adapter_version:
                continue
            for event in adapter.events:
                if event.delivery == Delivery.POLL and event.poll and event.ingress is None:
                    if not PollCursor.objects.filter(integration=connection, event_key=event.key).exists():
                        cursor = PollCursor(organization_id=tenant.organization_id, integration=connection, event_key=event.key, due_at=timezone.now())
                        cursor.definition = {"cursor": ""}
                        cursor.save()


def tick(tenant):
    discover(tenant)
    now = timezone.now()
    with tenant_atomic(tenant):
        rows = PollCursor.objects.select_for_update(skip_locked=True).filter(organization_id=tenant.organization_id,
            due_at__lte=now, integration__is_active=True, integration__status="OK").filter(
                Q(lease_until__isnull=True) | Q(lease_until__lte=now)).order_by("due_at", "pk")[:20]
        for row in rows:
            row.fence, row.lease_until = uuid.uuid4(), now + timedelta(seconds=90)
            row.due_at = row.lease_until
            row.save(update_fields=["fence", "lease_until", "due_at"])
            enqueue_event(DomainEvent(aggregate_type="service_poll", aggregate_id=str(row.pk),
                event_type="integrations.poll", payload={"cursorId": row.pk, "fence": str(row.fence)},
                tenant_context=system_context(tenant)))


def poll(tenant, pk, fence, *, registry=None):
    try:
        with tenant_atomic(tenant):
            row = PollCursor.objects.select_related("integration").get(pk=pk, organization_id=tenant.organization_id)
            if str(row.fence) != fence or row.lease_until is None or row.lease_until <= timezone.now():
                return
            connection = row.integration
            if not connection.is_active or connection.status != "OK":
                raise ExecutionDenied("connection_paused")
            settings, adapter, method = resolve(connection, registry)
            event = next((e for e in adapter.events if e.key == row.event_key and e.poll and e.delivery == Delivery.POLL and e.ingress is None), None)
            if event is None:
                raise ExecutionDenied("event_unavailable")
            context = build_context(tenant=tenant, integration=connection, method=method,
                settings=settings.settings, credentials=json.loads(settings.credentials or "{}"),
                registry=registry or default_registry(), transport_ref=adapter.transport)
            previous = row.definition["cursor"]
        result = event.poll(replace(context, deadline_seconds=30), previous)
        commit(tenant, pk, fence, previous, result, event)
    except Exception:
        # Remote responses/credentials never enter operational errors or logs.
        with tenant_atomic(tenant):
            row = PollCursor.objects.select_for_update().get(pk=pk, organization_id=tenant.organization_id)
            if str(row.fence) == fence:
                row.failures += 1
                row.error_code, row.lease_until = "event_unavailable", None
                row.due_at = timezone.now() + timedelta(seconds=min(3600, 30 * 2 ** min(row.failures, 7)))
                row.save(update_fields=["failures", "error_code", "lease_until", "due_at"])


def commit(tenant, pk, fence, previous, result, event):
    if (not isinstance(result, PollResult) or not isinstance(result.cursor, str) or len(result.cursor) > 8192
            or not isinstance(result.events, tuple) or len(result.events) > 100
            or type(result.retry_after) is not int or not 1 <= result.retry_after <= 86400):
        raise ExecutionDenied("event_invalid")
    for envelope in result.events:
        validate_envelope(event, envelope)
    with tenant_atomic(tenant):
        row = PollCursor.objects.select_for_update().get(pk=pk, organization_id=tenant.organization_id)
        if str(row.fence) != fence or row.lease_until is None or row.lease_until <= timezone.now() or row.definition["cursor"] != previous:
            return False
        connection = Integration.objects.select_for_update().get(pk=row.integration_id)
        if not connection.is_active or connection.status != "OK":
            raise ExecutionDenied("connection_paused")
        for envelope in result.events:
            persist(tenant, row.integration_id, envelope, replay_seconds=event.replay_seconds)
        row.definition = {"cursor": result.cursor}
        row.failures, row.error_code, row.lease_until = 0, "", None
        row.due_at = timezone.now() + timedelta(seconds=result.retry_after)
        row.save()
        return True


@register("integrations.poll", manages_own_transaction=True)
def dispatch(payload, tenant):
    from chatballs.integrations.execution.worker import submit_io
    # If the shared lane is full, the durable 90s lease becomes due again.
    submit_io(poll, tenant, payload["cursorId"], payload["fence"])
