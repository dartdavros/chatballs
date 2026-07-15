import hashlib
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.conversations.models import Contact, Conversation
from hub_platform.orders.models import FulfillmentStatus, Order, OrderItem, PaymentStatus
from hub_platform.products.models import Offer, Price, Product
from hub_platform.tenancy.context import TenantContext


def hash_ingest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OrderItemInput:
    offer_id: int
    price_id: int | None = None
    quantity: int = 1


def _active_price(offer: Offer) -> Price | None:
    return offer.prices.filter(is_active=True).order_by("-version").first()


@transaction.atomic
def create_order(
    *,
    context: TenantContext,
    contact: Contact,
    items: list[OrderItemInput],
    conversation: Conversation | None = None,
) -> Order:
    organization = context.organization
    if not items:
        raise ValidationError({"items": "Order needs at least one item"})
    if contact.organization_id != organization.id:
        raise ValidationError({"contact": "Contact belongs to another organization"})

    resolved: list[tuple[Offer, Price | None, int, int]] = []
    product = None
    currency = "RUB"
    total = 0
    for item in items:
        try:
            offer = Offer.objects.select_related("product").get(id=item.offer_id, product__organization=organization)
        except Offer.DoesNotExist as error:
            raise ValidationError({"items": f"Offer {item.offer_id} not found"}) from error
        price = None
        if item.price_id is not None:
            price = offer.prices.filter(id=item.price_id).first()
            if price is None:
                raise ValidationError({"items": f"Price {item.price_id} not found for offer {offer.code}"})
        else:
            price = _active_price(offer)
        quantity = max(1, int(item.quantity))
        unit = price.amount_minor if price else 0
        currency = price.currency if price else currency
        product = product or offer.product
        total += unit * quantity
        resolved.append((offer, price, quantity, unit * quantity))

    order = Order.objects.create(
        organization=organization,
        contact=contact,
        conversation=conversation,
        product=product,
        channel=conversation.channel if conversation else None,
        amount_minor=total,
        currency=currency,
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                organization=organization,
                order=order,
                offer=offer,
                price=price,
                title=offer.name,
                quantity=quantity,
                amount_minor=amount,
                currency=currency,
            )
            for offer, price, quantity, amount in resolved
        ]
    )
    return order


def mark_paid(*, context: TenantContext, order: Order) -> Order:
    if order.organization_id != context.organization_id:
        raise ValidationError({"order": "Order belongs to another organization"})
    if order.payment_status != PaymentStatus.PAID:
        order.payment_status = PaymentStatus.PAID
        order.paid_at = timezone.now()
        if order.fulfillment_status == FulfillmentStatus.NONE:
            order.fulfillment_status = FulfillmentStatus.PENDING
        order.save(update_fields=["payment_status", "paid_at", "fulfillment_status", "updated_at"])
    return order


def cancel_order(*, context: TenantContext, order: Order) -> Order:
    if order.organization_id != context.organization_id:
        raise ValidationError({"order": "Order belongs to another organization"})
    order.payment_status = PaymentStatus.CANCELLED
    order.save(update_fields=["payment_status", "updated_at"])
    return order


def set_fulfillment(*, context: TenantContext, order: Order, status: str) -> Order:
    if order.organization_id != context.organization_id:
        raise ValidationError({"order": "Order belongs to another organization"})
    if status not in FulfillmentStatus.values:
        raise ValidationError({"fulfillmentStatus": "Unknown status"})
    order.fulfillment_status = status
    order.save(update_fields=["fulfillment_status", "updated_at"])
    return order


# --- Ingest from a product backend (webhook, ADR-HUB-0018) ---


@dataclass(frozen=True)
class IngestItemInput:
    offer_code: str
    quantity: int = 1


@transaction.atomic
def ingest_order(
    *,
    context: TenantContext,
    product: Product,
    external_id: str,
    items: list[IngestItemInput],
    payment_status: str,
    currency: str = "RUB",
    amount_minor: int | None = None,
    conversation: Conversation | None = None,
    contact_name: str = "",
) -> tuple[Order, bool]:
    if payment_status not in PaymentStatus.values:
        raise ValidationError({"paymentStatus": "Unknown status"})
    if not items:
        raise ValidationError({"items": "Order needs at least one item"})
    organization = context.organization
    if product.organization_id != context.organization_id:
        raise ValidationError({"product": "Product belongs to another organization"})

    # Идемпотентность по (организация, продукт, внешний id).
    if external_id:
        existing = Order.objects.filter(organization=organization, source=product.code, external_id=external_id).first()
        if existing is not None:
            return existing, False

    resolved: list[tuple[Offer, Price | None, int, int]] = []
    total = 0
    for item in items:
        try:
            offer = Offer.objects.get(product=product, code=item.offer_code)
        except Offer.DoesNotExist as error:
            raise ValidationError({"items": f"Offer {item.offer_code} not found in {product.code}"}) from error
        price = _active_price(offer)
        quantity = max(1, int(item.quantity))
        unit = price.amount_minor if price else 0
        if price:
            currency = price.currency
        total += unit * quantity
        resolved.append((offer, price, quantity, unit * quantity))

    if conversation is not None:
        contact = conversation.contact
    else:
        contact = Contact.objects.create(organization=organization, name=contact_name or "Клиент")

    is_paid = payment_status == PaymentStatus.PAID
    order = Order.objects.create(
        organization=organization,
        contact=contact,
        conversation=conversation,
        product=product,
        channel=conversation.channel if conversation else None,
        payment_status=payment_status,
        fulfillment_status=FulfillmentStatus.PENDING if is_paid else FulfillmentStatus.NONE,
        amount_minor=amount_minor if amount_minor is not None else total,
        currency=currency,
        source=product.code,
        external_id=external_id,
        paid_at=timezone.now() if is_paid else None,
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                organization=organization,
                order=order,
                offer=offer,
                price=price,
                title=offer.name,
                quantity=quantity,
                amount_minor=amount,
                currency=currency,
            )
            for offer, price, quantity, amount in resolved
        ]
    )
    return order, True
