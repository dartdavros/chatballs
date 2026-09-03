from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.identity.models import Department, Organization
from hub_platform.products.models import Product, ProductDepartment, ProductStatus
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.usage_service import record_usage
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True)
class ProductInput:
    code: str
    name: str
    site_url: str = ""
    department_ids: tuple[int, ...] = ()


def _departments(organization: Organization, department_ids: tuple[int, ...]) -> list[Department]:
    if not department_ids:
        return []
    departments = list(Department.objects.filter(organization=organization, id__in=department_ids))
    if len(departments) != len(set(department_ids)):
        raise ValidationError({"departmentIds": "Department not found"})
    return departments


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
    record_usage(
        context=context,
        quota_key=QuotaKey.PRODUCTS,
        quantity=1,
        idempotency_key=f"product:{product.id}",
        source="product.created",
        aggregate_type="Product",
        aggregate_id=str(product.id),
    )
    for department in _departments(organization, data.department_ids):
        ProductDepartment.objects.create(product=product, department=department)
    return product


@transaction.atomic
def update_product(*, context: TenantContext, product: Product, data: ProductInput) -> Product:
    if product.organization_id != context.organization_id:
        raise ValidationError({"product": "Product belongs to another organization"})
    product.name = data.name.strip()
    product.site_url = data.site_url.strip()
    product.full_clean(exclude=["code"])
    product.save(update_fields=["name", "site_url", "updated_at"])
    departments = _departments(product.organization, data.department_ids)
    product.department_links.exclude(department__in=departments).delete()
    for department in departments:
        ProductDepartment.objects.get_or_create(product=product, department=department)
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
