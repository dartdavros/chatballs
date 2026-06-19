from django.db.models import Prefetch, QuerySet

from hub_platform.products.models import Offer, Product


def products_for_organization(organization_id: int) -> QuerySet[Product]:
    offers = Offer.objects.prefetch_related("prices").order_by("name")
    return (
        Product.objects.filter(organization_id=organization_id)
        .prefetch_related("department_links__department", Prefetch("offers", queryset=offers))
        .order_by("name")
    )


def product_for_organization(*, organization_id: int, product_id: int) -> Product:
    return products_for_organization(organization_id).get(id=product_id)
