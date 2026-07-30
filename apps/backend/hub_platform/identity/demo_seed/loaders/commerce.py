"""Коммерция: заказы, позиции, продажи (через application-сервис), атрибуция.

Продажи создаются через канонический ``record_product_sales_event`` (ADR-HUB-0025),
а не прямой ORM-write в Sale — это соблюдает append-only контракт журнала.
Заказы (Hub Order) создаются напрямую, как и в существующем сиде.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.orders.models import FulfillmentStatus, Order, OrderItem, PaymentStatus
from hub_platform.sales.models import (
    ActorType,
    AttributionToken,
    Environment,
    ExternalCustomerIdentity,
)
from hub_platform.sales.services import record_product_sales_event
from hub_platform.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("commerce")
    now = timezone.now()

    for item in data.get("orders", []):
        _ensure_order(refs, item, now)

    for item in data.get("sales", []):
        _ensure_sale(context, refs, item)

    for item in data.get("externalCustomers", []):
        _ensure_external_customer(refs, item)

    for item in data.get("attributionTokens", []):
        _ensure_attribution_token(refs, item, now)


def _ensure_order(refs: DemoRefs, item: dict, now) -> None:
    payment_status = item["paymentStatus"]
    order, created = Order.objects.get_or_create(
        organization=refs.organization,
        source="demo-seed",
        external_id=item["externalId"],
        defaults={
            "product": refs.products[item["product"]],
            "contact": refs.contacts[item["contact"]],
            "conversation": refs.conversations.get(item.get("conversation")),
            "channel": refs.channels[item["channel"]],
            "payment_status": payment_status,
            "fulfillment_status": item.get("fulfillmentStatus", FulfillmentStatus.NONE),
            "amount_minor": item["amountMinor"],
            "paid_at": now if payment_status == PaymentStatus.PAID else None,
        },
    )
    if created:
        for line in item.get("items", []):
            OrderItem.objects.get_or_create(
                order=order,
                offer=refs.offers[line["offer"]],
                defaults={
                    "price": refs.prices.get(line.get("price")),
                    "title": line["title"],
                    "quantity": line.get("quantity", 1),
                    "amount_minor": line["amountMinor"],
                },
            )


def _ensure_sale(context: TenantContext, refs: DemoRefs, item: dict) -> None:
    source = refs.sales_sources[item["salesSource"]]
    occurred_at = timezone.now() - timedelta(days=item.get("daysAgo", 0))
    sale_block = {
        "external_sale_id": item["externalSaleId"],
        "amount_minor": item["amountMinor"],
        "refunded_amount_minor": item.get("refundedAmountMinor", 0),
        "currency": item.get("currency", "RUB"),
        "items": item.get("items", []),
    }
    payload = {
        "schema_version": 1,
        "event_id": item["eventId"],
        "event_type": item["eventType"],
        "occurred_at": occurred_at.isoformat(),
        "sale": sale_block,
        "metadata": item.get("metadata", {}),
    }
    record_product_sales_event(context=context, source=source, payload=payload)


def _ensure_external_customer(refs: DemoRefs, item: dict) -> None:
    ExternalCustomerIdentity.objects.get_or_create(
        organization=refs.organization,
        product=refs.products[item["product"]],
        external_customer_id=item["externalCustomerId"],
        defaults={
            "contact": refs.contacts[item["contact"]],
            "environment": item.get("environment", Environment.PRODUCTION),
        },
    )


def _ensure_attribution_token(refs: DemoRefs, item: dict, now) -> None:
    import hashlib
    import secrets

    token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    AttributionToken.objects.get_or_create(
        token_hash=token_hash,
        defaults={
            "organization": refs.organization,
            "product": refs.products[item["product"]],
            "offer": refs.offers.get(item.get("offer")),
            "contact": refs.contacts[item["contact"]],
            "conversation": refs.conversations[item["conversation"]],
            "channel": refs.channels.get(item.get("channel")),
            "connection": refs.integrations.get(item.get("connection")),
            "actor_type": item.get("actorType", ActorType.AI_AGENT),
            "actor_id": item.get("actorId", ""),
            "expires_at": now + timedelta(days=item.get("ttlDays", 30)),
        },
    )
