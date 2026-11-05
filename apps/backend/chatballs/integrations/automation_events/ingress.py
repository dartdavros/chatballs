"""Trusted adapter verification followed by receipt + outbox before ACK."""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta

from django.utils import timezone

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.adapters.events import VerifiedEvent
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution.events import system_context
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.integrations.service_connections.binding import build_context, resolve
from chatballs.tenancy.database import tenant_atomic


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def receive(tenant, connection_id, event_key, body, headers, *, registry=None):
    if len(body) > 256 * 1024:
        raise ExecutionDenied("budget_volume")
    registry = registry or default_registry()
    with tenant_atomic(tenant):
        integration = Integration.objects.get(pk=connection_id, organization_id=tenant.organization_id)
        row, adapter, method = resolve(integration, registry)
        event = next((e for e in adapter.events if e.key == event_key), None)
        if event is None or not event.ingress or not event.replay_seconds or not 1 <= event.replay_seconds <= 31536000:
            raise ExecutionDenied("event_unavailable")
        context = build_context(tenant=tenant, integration=integration, method=method,
            settings=row.settings, credentials=json.loads(row.credentials or "{}"), registry=registry,
            transport_ref=adapter.transport)
    # Signature verification is an adapter responsibility over the original bytes.
    try:
        envelope = event.ingress(context, body, headers)
    except Exception:
        raise ExecutionDenied("event_invalid") from None
    validate_envelope(event, envelope)
    return persist(tenant, connection_id, envelope, replay_seconds=event.replay_seconds)


def validate_envelope(event, envelope):
    if (not event.replay_seconds or not 1 <= event.replay_seconds <= 31536000
            or not isinstance(envelope, VerifiedEvent) or envelope.event_key != event.key
            or not isinstance(envelope.event_id, str) or not 1 <= len(envelope.event_id) <= 512
            or not isinstance(envelope.correlation, str) or len(envelope.correlation) > 512
            or not isinstance(envelope.occurred_at, datetime) or timezone.is_naive(envelope.occurred_at)
            or validate_value(event.payload, envelope.payload)
            or not isinstance(envelope.causal_chain, tuple) or len(envelope.causal_chain) > 16
            or any(not isinstance(item, str) or not 1 <= len(item) <= 160 for item in envelope.causal_chain)
            or not isinstance(envelope.entity_kind, str) or len(envelope.entity_kind) > 100
            or not isinstance(envelope.entity_id, str) or len(envelope.entity_id) > 512
            or bool(envelope.entity_kind) != bool(envelope.entity_id)
            or envelope.sequence is not None and (type(envelope.sequence) is not int or envelope.sequence < 0)):
        raise ExecutionDenied("event_invalid")
    now = timezone.now()
    if not now - timedelta(seconds=event.replay_seconds) <= envelope.occurred_at <= now + timedelta(minutes=5):
        raise ExecutionDenied("event_expired")


def persist(tenant, connection_id, envelope, *, replay_seconds, audience=None):
    now = timezone.now()
    result = asdict(envelope.result) if envelope.result else None
    if result and result.get("deadline"):
        result["deadline"] = result["deadline"].isoformat()
    content = {"payload": envelope.payload, "result": result, "event": envelope.event_key,
               "correlation": envelope.correlation, "sequence": envelope.sequence, "causalChain": list(envelope.causal_chain),
               "entityKind": envelope.entity_kind, "entityId": envelope.entity_id}
    encoded = json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode()) > 256 * 1024:
        raise ExecutionDenied("budget_volume")
    source = f"service:{connection_id}" if connection_id else "chatballs"
    with tenant_atomic(tenant):
        # Serializes duplicate IDs without catching an integrity error in a broken transaction.
        if connection_id:
            Integration.objects.select_for_update().get(pk=connection_id, organization_id=tenant.organization_id)
        else:
            from chatballs.identity.models import Organization
            Organization.objects.select_for_update().get(pk=tenant.organization_id)
        row = EventReceipt.objects.filter(organization_id=tenant.organization_id, source_key=source,
            event_id_hash=digest(envelope.event_id)).first()
        if row:
            if row.digest != digest(encoded):
                raise ExecutionDenied("event_conflict")
            return row, False
        row = EventReceipt(organization_id=tenant.organization_id, integration_id=connection_id,
            source_key=source, event_id_hash=digest(envelope.event_id), event_key=envelope.event_key,
            digest=digest(encoded), correlation_hash=digest(envelope.correlation), sequence=envelope.sequence,
            occurred_at=envelope.occurred_at, expires_at=now + timedelta(seconds=replay_seconds))
        row.definition = content
        row.save()
        from chatballs.integrations.automation_events.fanout import seed
        seed(tenant, row, scenario_id=audience)
        enqueue_event(DomainEvent(aggregate_type="service_receipt", aggregate_id=str(row.pk),
            event_type="integrations.receipt", payload={"receiptId": row.pk}, tenant_context=system_context(tenant)))
        return row, True
