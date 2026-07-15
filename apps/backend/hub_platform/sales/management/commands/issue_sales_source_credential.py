"""Создать (или найти) PRODUCT_API SalesSource продукта и выпустить Bearer-ключ.

Открытый ключ печатается ОДИН раз — сохраните его в конфиге backend продукта.
Повторный запуск ротирует ключ (старый становится недействительным). Запускать
осознанно (см. глобальное правило про credentials).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from hub_platform.identity.models import Organization
from hub_platform.products.models import Product
from hub_platform.sales.models import Environment, SalesSource, SalesSourceType
from hub_platform.sales.services import issue_sales_source_credential
from hub_platform.tenancy.context import TenantActorKind, TenantContext
from hub_platform.tenancy.database import tenant_atomic


class Command(BaseCommand):
    help = "Provision a Product Sales API source for a product and print its Bearer key once."

    def add_arguments(self, parser) -> None:
        parser.add_argument("product_code")
        parser.add_argument("--organization", required=True, help="Organization public UUID")
        parser.add_argument("--code", default="product-api", help="SalesSource code (unique per product)")
        parser.add_argument("--environment", default=Environment.PRODUCTION, choices=Environment.values)

    def handle(self, *args: object, **options: object) -> None:
        code = str(options["product_code"])
        try:
            organization = Organization.objects.get(public_id=options["organization"])
        except (Organization.DoesNotExist, ValueError) as error:
            raise CommandError("Unknown organization public UUID") from error
        context = TenantContext.for_resource(
            organization,
            actor_kind=TenantActorKind.SYSTEM,
        )
        with tenant_atomic(context):
            product = Product.objects.filter(
                organization=organization, code=code
            ).select_related("organization").first()
            if product is None:
                raise CommandError(f"product '{code}' not found")

            source, created = SalesSource.objects.get_or_create(
                organization=product.organization,
                product=product,
                code=str(options["code"]),
                defaults={"type": SalesSourceType.PRODUCT_API, "environment": str(options["environment"])},
            )
            raw = issue_sales_source_credential(source=source)
        verb = "created" if created else "rotated"
        self.stdout.write(self.style.SUCCESS(f"Product Sales API source {verb} for {code} ({source.environment}); key (shown once):"))
        self.stdout.write(raw)
