from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.identity.models import Department, Organization
from hub_platform.products.models import Offer, Price, Product, ProductDepartment, ProductStatus


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


# --- Offers (catalog lives in Hub, ADR-HUB-0018) ---


@dataclass(frozen=True)
class OfferInput:
    code: str
    name: str
    description: str = ""
    fulfillment_type: str = ""
    payment_type: str = ""
    is_active: bool = True
    ai_offerable: bool = False
    primary_box_offer_id: int | None = None


def _primary_box_offer(product: Product, primary_box_offer_id: int | None) -> Offer | None:
    if primary_box_offer_id is None:
        return None
    try:
        return product.offers.get(id=primary_box_offer_id)
    except Offer.DoesNotExist as error:
        raise ValidationError({"primaryBoxOfferId": "Offer not found"}) from error


@transaction.atomic
def create_offer(*, product: Product, data: OfferInput) -> Offer:
    offer = Offer(
        product=product,
        code=data.code.strip().lower(),
        name=data.name.strip(),
        description=data.description.strip(),
        fulfillment_type=data.fulfillment_type,
        payment_type=data.payment_type,
        is_active=data.is_active,
        ai_offerable=data.ai_offerable,
        primary_box_offer=_primary_box_offer(product, data.primary_box_offer_id),
    )
    offer.full_clean()
    offer.save()
    return offer


@transaction.atomic
def update_offer(*, offer: Offer, data: OfferInput) -> Offer:
    # Код предложения неизменяем; всё остальное редактируется.
    offer.name = data.name.strip()
    offer.description = data.description.strip()
    offer.fulfillment_type = data.fulfillment_type
    offer.payment_type = data.payment_type
    offer.is_active = data.is_active
    offer.ai_offerable = data.ai_offerable
    offer.primary_box_offer = _primary_box_offer(offer.product, data.primary_box_offer_id)
    offer.full_clean(exclude=["code"])
    offer.save()
    return offer


# --- Prices (immutable versions, ADR-HUB-0018) ---


@dataclass(frozen=True)
class PriceInput:
    amount_minor: int
    billing_period: str
    currency: str = "RUB"
    valid_from: datetime | None = None


@transaction.atomic
def add_price_version(*, offer: Offer, data: PriceInput) -> Price:
    # Новая версия цены архивирует прежнюю активную в той же валюте/периоде.
    valid_from = data.valid_from or timezone.now()
    same_line = Price.objects.filter(offer=offer, currency=data.currency, billing_period=data.billing_period)
    same_line.filter(is_active=True).update(is_active=False, valid_until=valid_from)
    last = same_line.order_by("-version").first()
    price = Price(
        offer=offer,
        version=last.version + 1 if last is not None else 1,
        amount_minor=data.amount_minor,
        currency=data.currency,
        billing_period=data.billing_period,
        valid_from=valid_from,
        is_active=True,
    )
    price.full_clean()
    price.save()
    return price
