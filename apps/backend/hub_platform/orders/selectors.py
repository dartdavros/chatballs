from django.db.models import QuerySet

from hub_platform.orders.models import Order


def orders_for_organization(organization_id: int) -> QuerySet[Order]:
    return (
        Order.objects.filter(organization_id=organization_id)
        .select_related("contact", "product", "channel", "conversation")
        .prefetch_related("items")
        .order_by("-created_at")
    )


def order_for_organization(*, organization_id: int, order_id: int) -> Order:
    return orders_for_organization(organization_id).get(id=order_id)
