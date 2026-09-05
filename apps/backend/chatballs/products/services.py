from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.products.models import Product, ProductStatus
from chatballs.tenancy.context import TenantContext


@dataclass(frozen=True)
class ProductInput:
    code: str
    name: str
    site_url: str = ""


@transaction.atomic
def create_product(*, context: TenantContext, data: ProductInput) -> Product:
    organization = context.organization
    product = Product(
        organization=organization,
        code=data.code.strip().lower(),
        name=data.name.strip(),
        status=ProductStatus.ACTIVE,
        site_url=data.site_url.strip(),
    )
    product.full_clean()
    product.save()
    return product


@transaction.atomic
def update_product(*, context: TenantContext, product: Product, data: ProductInput) -> Product:
    if product.organization_id != context.organization_id:
        raise ValidationError({"product": "Product belongs to another organization"})
    product.name = data.name.strip()
    product.site_url = data.site_url.strip()
    product.full_clean(exclude=["code"])
    product.save(update_fields=["name", "site_url", "updated_at"])
    return product


def set_product_status(
    *, context: TenantContext, product: Product, status: ProductStatus
) -> Product:
    if product.organization_id != context.organization_id:
        raise ValidationError({"product": "Product belongs to another organization"})
    if product.status != status:
        product.status = status
        product.save(update_fields=["status", "updated_at"])
    return product
