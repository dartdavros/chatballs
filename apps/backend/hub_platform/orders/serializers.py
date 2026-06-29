from hub_platform.orders.models import Order, OrderItem


def order_item_payload(item: OrderItem) -> dict[str, object]:
    return {
        "id": item.id,
        "offerCode": item.offer.code,
        "title": item.title,
        "quantity": item.quantity,
        "amountMinor": item.amount_minor,
        "currency": item.currency,
    }


def order_payload(order: Order, *, with_items: bool = False) -> dict[str, object]:
    payload = {
        "id": order.id,
        "code": order.code,
        "contact": {"id": order.contact_id, "name": order.contact.name},
        "conversationId": order.conversation_id,
        "product": {"code": order.product.code, "name": order.product.name} if order.product_id else None,
        "channel": order.channel.name if order.channel_id else None,
        "paymentStatus": order.payment_status,
        "fulfillmentStatus": order.fulfillment_status,
        "amountMinor": order.amount_minor,
        "currency": order.currency,
        "createdAt": order.created_at.isoformat(),
        "paidAt": order.paid_at.isoformat() if order.paid_at else None,
    }
    if with_items:
        payload["items"] = [order_item_payload(item) for item in order.items.all()]
    return payload
