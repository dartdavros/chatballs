"""Миграция legacy `orders` в домен продаж (ADR-HUB-0025 §11, SPEC-HUB-0014 §11).

По умолчанию — DRY-RUN: только отчёт по классам записей, без единой записи в БД.

Флаги (каждый включается ОСОЗНАННО владельцем):
  --apply              импортировать подтверждённые legacy-заказы в Sale/SaleEvent
                       (sale.legacy_imported). PENDING-заказы НЕ импортируются.
  --provision-sources  создать production SalesSource(PRODUCT_API) для каждого
                       продукта и скопировать действующий Product.ingest_token_hash
                       в credential_hash (§11 шаг 2-3). Это единственный шаг,
                       затрагивающий credential; секрет не генерируется и не ротируется.
  --product CODE       ограничить одним продуктом.

Команда НИКОГДА не удаляет legacy-данные, не отключает legacy write API и не
ротирует/очищает Product.ingest_token_hash — это отдельные шаги §11 (11-12),
требующие отдельного подтверждения владельца.
"""

from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db.models import QuerySet

from hub_platform.orders.models import Order
from hub_platform.identity.models import Organization
from hub_platform.products.models import Product
from hub_platform.sales.services import (
    LEGACY_CLASS_PENDING,
    classify_legacy_order,
    import_legacy_order,
    provision_product_sales_source,
)
from hub_platform.tenancy.context import TenantActorKind, TenantContext
from hub_platform.tenancy.database import tenant_atomic


class Command(BaseCommand):
    help = "Dry-run/import legacy orders into the sales domain (ADR-HUB-0025 §11)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--apply", action="store_true", help="Импортировать подтверждённые заказы в Sale/SaleEvent")
        parser.add_argument("--provision-sources", action="store_true", help="Создать SalesSource и скопировать ingest_token_hash")
        parser.add_argument("--product", default="", help="Код продукта (по умолчанию — все)")
        parser.add_argument("--organization", required=True, help="Organization public UUID")

    def _orders(self, context: TenantContext, product_code: str) -> QuerySet[Order]:
        orders = Order.objects.filter(organization=context.organization).select_related("organization", "product", "contact", "conversation").prefetch_related("items")
        if product_code:
            orders = orders.filter(product__code=product_code)
        return orders.order_by("id")

    def handle(self, *args: object, **options: object) -> None:
        try:
            organization = Organization.objects.get(public_id=options["organization"])
        except (Organization.DoesNotExist, ValueError) as error:
            raise CommandError("Unknown organization public UUID") from error
        context = TenantContext.for_resource(
            organization,
            actor_kind=TenantActorKind.SYSTEM,
        )
        with tenant_atomic(context):
            self._handle_for_tenant(context=context, options=options)

    def _handle_for_tenant(self, *, context: TenantContext, options: dict) -> None:
        apply = bool(options["apply"])
        provision = bool(options["provision_sources"])
        product_code = str(options["product"])

        orders = self._orders(context, product_code)
        classes = Counter(classify_legacy_order(order) for order in orders)
        total = sum(classes.values())

        self.stdout.write(self.style.MIGRATE_HEADING("Отчёт по legacy orders:"))
        self.stdout.write(f"  всего: {total}")
        for name in ("external", "manual", LEGACY_CLASS_PENDING):
            self.stdout.write(f"  {name}: {classes.get(name, 0)}")
        self.stdout.write(f"  импортируемых (external+manual): {classes.get('external', 0) + classes.get('manual', 0)}")
        self.stdout.write(f"  требуют ручного решения (PENDING): {classes.get(LEGACY_CLASS_PENDING, 0)}")

        if provision:
            self._provision(context, product_code)

        if not apply:
            self.stdout.write(self.style.WARNING("DRY-RUN: изменения не внесены. Повторите с --apply для импорта."))
            return

        created = 0
        skipped = 0
        pending = 0
        for order in orders:
            if classify_legacy_order(order) == LEGACY_CLASS_PENDING:
                pending += 1
                continue
            _, was_created = import_legacy_order(order=order)
            created += int(was_created)
            skipped += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"Импортировано: {created}; уже были: {skipped}; пропущено PENDING: {pending}"))
        self.stdout.write("Legacy orders НЕ удалены и остаются read-only источником до отдельного подтверждения владельца (§11 шаг 12).")

    def _provision(self, context: TenantContext, product_code: str) -> None:
        products = Product.objects.filter(organization=context.organization)
        if product_code:
            products = products.filter(code=product_code)
        self.stdout.write(self.style.MIGRATE_HEADING("Provisioning SalesSource:"))
        for product in products:
            source, created, copied = provision_product_sales_source(product=product)
            verb = "создан" if created else "существует"
            note = "; действующий token скопирован" if copied else ("; token уже задан" if source.credential_hash else "; token отсутствует — выпустите issue_sales_source_credential")
            self.stdout.write(f"  {product.code}: source {verb}{note}")
