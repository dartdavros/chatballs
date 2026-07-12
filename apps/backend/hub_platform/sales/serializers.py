from __future__ import annotations

from hub_platform.sales.models import Sale, SaleEvent, SalesSource


def sale_event_payload(event: SaleEvent) -> dict[str, object]:
    actor = None
    if event.actor_user_id:
        actor = {"id": event.actor_user_id, "name": getattr(event.actor_user, "email", "")}
    return {
        "id": event.id,
        "eventType": event.event_type,
        "sourceType": event.source_type,
        "schemaVersion": event.schema_version,
        "occurredAt": event.occurred_at.isoformat() if event.occurred_at else None,
        "receivedAt": event.received_at.isoformat() if event.received_at else None,
        "appliedAt": event.applied_at.isoformat() if event.applied_at else None,
        "processingStatus": event.processing_status,
        "processingError": event.processing_error,
        "actor": actor,
    }


def sale_payload(sale: Sale, *, with_events: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": sale.id,
        "product": {"code": sale.product.code, "name": sale.product.name} if sale.product_id else None,
        "environment": sale.environment,
        "sourceType": sale.source_type,
        "externalSaleId": sale.external_sale_id,
        "externalCustomerId": sale.external_customer_id,
        "contact": {"id": sale.contact_id, "name": sale.contact.name} if sale.contact_id else None,
        "conversationId": sale.conversation_id,
        "status": sale.status,
        "amountMinor": sale.amount_minor,
        "refundedAmountMinor": sale.refunded_amount_minor,
        "netAmountMinor": sale.net_amount_minor,
        "currency": sale.currency,
        "occurredAt": sale.occurred_at.isoformat() if sale.occurred_at else None,
        "lastEventAt": sale.last_event_at.isoformat() if sale.last_event_at else None,
        "attributionMethod": sale.attribution_method,
        "attributedActor": (
            {"type": sale.attributed_actor_type, "id": sale.attributed_actor_id}
            if sale.attributed_actor_type
            else None
        ),
        "source": {"id": sale.sales_source_id, "code": sale.sales_source.code} if sale.sales_source_id else None,
        "lineItems": sale.line_items_snapshot,
        "metadata": sale.metadata,
        "createdAt": sale.created_at.isoformat(),
        "updatedAt": sale.updated_at.isoformat(),
    }
    if with_events:
        payload["events"] = [sale_event_payload(event) for event in sale.events.select_related("actor_user").order_by("received_at", "id")]
    return payload


def sales_source_payload(source: SalesSource) -> dict[str, object]:
    return {
        "id": source.id,
        "product": {"code": source.product.code, "name": source.product.name},
        "code": source.code,
        "type": source.type,
        "environment": source.environment,
        "status": source.status,
        "credentialHint": source.credential_hint,
        "allowedSchemaVersions": source.allowed_schema_versions,
        "lastEventAt": source.last_event_at.isoformat() if source.last_event_at else None,
        "lastErrorAt": source.last_error_at.isoformat() if source.last_error_at else None,
        "lastError": source.last_error,
        "createdAt": source.created_at.isoformat(),
    }
