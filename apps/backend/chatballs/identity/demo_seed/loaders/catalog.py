"""Каталог: продукты (скрытая техническая привязка, ADR-HUB-0041)."""

from __future__ import annotations

from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.products.models import Product, ProductStatus
from chatballs.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("catalog")
    organization = refs.organization

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
