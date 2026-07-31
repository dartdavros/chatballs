from django.db.models import Prefetch, QuerySet

from hub_platform.products.models import Offer, Product
from hub_platform.tenancy.context import TenantContext


def products_for_context(context: TenantContext) -> QuerySet[Product]:
    offers = Offer.objects.prefetch_related("prices").order_by("name")
    return (
        Product.objects.filter(organization_id=context.organization_id)
        .prefetch_related(
            "department_links__department",
            Prefetch("offers", queryset=offers),
            "channels__ai_agent",
            "channels__connections",
        )
        .order_by("name")
    )


def product_for_context(*, context: TenantContext, product_id: int) -> Product:
    return products_for_context(context).get(id=product_id)
