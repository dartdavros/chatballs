"""Каталог: продукты, офферы, цены, связи отделов, источники продаж."""

from __future__ import annotations

from django.utils import timezone

from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.products.models import (
    Offer,
    Price,
    Product,
    ProductDepartment,
    ProductStatus,
)
from hub_platform.sales.models import Environment, SalesSource, SalesSourceStatus, SalesSourceType
from hub_platform.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("catalog")
    organization = refs.organization
    now = timezone.now()

    for item in data["products"]:
        product, _ = Product.objects.get_or_create(
            organization=organization,
            code=item["code"],
            defaults={
                "name": item["name"],
                "status": ProductStatus.ACTIVE,
                "site_url": item.get("siteUrl", ""),
            },
        )
        refs.products[item["code"]] = product
        for department_code in item.get("departments", []):
            department = refs.departments.get(department_code)
            if department is not None:
                ProductDepartment.objects.get_or_create(product=product, department=department)

    for item in data["offers"]:
        _ensure_offer(refs, item)

    for item in data["prices"]:
        _ensure_price(refs, item, now)

    for item in data.get("salesSources", []):
        _ensure_sales_source(refs, item)


def _ensure_offer(refs: DemoRefs, item: dict) -> None:
    product = refs.products[item["product"]]
    primary_box = None
    if item.get("primaryBoxOffer"):
        primary_box = refs.offers[item["primaryBoxOffer"]]
    offer, _ = Offer.objects.get_or_create(
        product=product,
        code=item["code"],
        defaults={
            "name": item["name"],
            "description": item.get("description", ""),
            "fulfillment_type": item["fulfillmentType"],
            "payment_type": item["paymentType"],
            "primary_box_offer": primary_box,
            "fiscal_name": item.get("fiscalName", ""),
            "is_active": True,
            "ai_offerable": item.get("aiOfferable", False),
        },
    )
    refs.offers[item["key"]] = offer


def _ensure_price(refs: DemoRefs, item: dict, now) -> None:
    offer = refs.offers[item["offer"]]
    valid_from = now
    price, _ = Price.objects.get_or_create(
        offer=offer,
        currency=item.get("currency", "RUB"),
        billing_period=item["billingPeriod"],
        version=1,
        defaults={
            "amount_minor": item["amountMinor"],
            "valid_from": valid_from,
            "is_active": True,
        },
    )
    refs.prices[item["key"]] = price


def _ensure_sales_source(refs: DemoRefs, item: dict) -> None:
    product = refs.products[item["product"]]
    source, _ = SalesSource.objects.get_or_create(
        organization=refs.organization,
        product=product,
        code=item["code"],
        defaults={
            "type": SalesSourceType.PRODUCT_API,
            "environment": item.get("environment", Environment.PRODUCTION),
            "status": item.get("status", SalesSourceStatus.ACTIVE),
            "credential_hint": item.get("credentialHint", ""),
        },
    )
    refs.sales_sources[item["key"]] = source
