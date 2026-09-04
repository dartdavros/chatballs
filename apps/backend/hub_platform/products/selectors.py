from django.db.models import QuerySet

from hub_platform.products.models import Product
from hub_platform.tenancy.context import TenantContext


def products_for_context(context: TenantContext) -> QuerySet[Product]:
    return (
        Product.objects.filter(organization_id=context.organization_id)
        .prefetch_related(
            "channels__ai_agent",
            "channels__connections",
        )
        .order_by("name")
    )


def product_for_context(*, context: TenantContext, product_id: int) -> Product:
    return products_for_context(context).get(id=product_id)
