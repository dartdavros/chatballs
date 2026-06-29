from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.conversations.models import Contact, Conversation
from hub_platform.orders.models import FulfillmentStatus, Order, OrderItem, PaymentStatus
from hub_platform.products.models import Offer, Price


@dataclass(frozen=True)
class OrderItemInput:
    offer_id: int
    price_id: int | None = None
    quantity: int = 1


def _active_price(offer: Offer) -> Price | None:
    return offer.prices.filter(is_active=True).order_by("-version").first()


@transaction.atomic
def create_order(*, organization, contact: Contact, items: list[OrderItemInput], conversation: Conversation | None = None) -> Order:
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
            OrderItem(order=order, offer=offer, price=price, title=offer.name, quantity=quantity, amount_minor=amount, currency=currency)
            for offer, price, quantity, amount in resolved
        ]
    )
    return order


def mark_paid(*, order: Order) -> Order:
    if order.payment_status != PaymentStatus.PAID:
        order.payment_status = PaymentStatus.PAID
        order.paid_at = timezone.now()
        if order.fulfillment_status == FulfillmentStatus.NONE:
            order.fulfillment_status = FulfillmentStatus.PENDING
        order.save(update_fields=["payment_status", "paid_at", "fulfillment_status", "updated_at"])
    return order


def cancel_order(*, order: Order) -> Order:
    order.payment_status = PaymentStatus.CANCELLED
    order.save(update_fields=["payment_status", "updated_at"])
    return order


def set_fulfillment(*, order: Order, status: str) -> Order:
    if status not in FulfillmentStatus.values:
        raise ValidationError({"fulfillmentStatus": "Unknown status"})
    order.fulfillment_status = status
    order.save(update_fields=["fulfillment_status", "updated_at"])
    return order
