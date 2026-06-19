from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.identity.models import Department, Organization
from hub_platform.products.models import Product, ProductDepartment, ProductStatus


@dataclass(frozen=True)
class ProductInput:
    code: str
    name: str
    site_url: str = ""
    summary: str = ""
    sales_description: str = ""
    department_ids: tuple[int, ...] = ()


def _departments(organization: Organization, department_ids: tuple[int, ...]) -> list[Department]:
    if not department_ids:
        return []
    departments = list(Department.objects.filter(organization=organization, id__in=department_ids))
    if len(departments) != len(set(department_ids)):
        raise ValidationError({"departmentIds": "Department not found"})
    return departments


@transaction.atomic
def create_product(*, organization: Organization, data: ProductInput) -> Product:
    product = Product(
        organization=organization,
        code=data.code.strip().lower(),
        name=data.name.strip(),
        status=ProductStatus.ACTIVE,
        site_url=data.site_url.strip(),
        summary=data.summary.strip(),
        sales_description=data.sales_description.strip(),
    )
    product.full_clean()
    product.save()
    for department in _departments(organization, data.department_ids):
        ProductDepartment.objects.create(product=product, department=department)
    return product


@transaction.atomic
def update_product(*, product: Product, data: ProductInput) -> Product:
    product.name = data.name.strip()
    product.site_url = data.site_url.strip()
    product.summary = data.summary.strip()
    product.sales_description = data.sales_description.strip()
    product.full_clean(exclude=["code"])
    product.save(update_fields=["name", "site_url", "summary", "sales_description", "updated_at"])
    departments = _departments(product.organization, data.department_ids)
    product.department_links.exclude(department__in=departments).delete()
    for department in departments:
        ProductDepartment.objects.get_or_create(product=product, department=department)
    return product


def set_product_status(*, product: Product, status: ProductStatus) -> Product:
    if product.status != status:
        product.status = status
        product.save(update_fields=["status", "updated_at"])
    return product
