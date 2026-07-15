from django.db.models import QuerySet

from hub_platform.orders.models import Order
from hub_platform.tenancy.context import TenantContext


def orders_for_context(context: TenantContext) -> QuerySet[Order]:
    return (
        Order.objects.filter(organization_id=context.organization_id)
        .select_related("contact", "product", "channel", "conversation")
        .prefetch_related("items")
        .order_by("-created_at")
    )


def order_for_context(*, context: TenantContext, order_id: int) -> Order:
    return orders_for_context(context).get(id=order_id)
