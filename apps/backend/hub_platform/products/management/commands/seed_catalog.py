"""Seed the management catalog (offers + prices) for FirePage and Foxray.

Hub owns the commercial catalog (ADR-HUB-0018). Prices live here. The actual
charge happens in the product backend. This command is idempotent and reflects
the live offerings on firepage.ru and foxray.pro.

FirePage keeps a single product with one box-license offer per ready site
(one site = one license), so the FirePage sales agent stays one-per-product.
Foxray is one product with subscription tariffs (free / Pro / Max).
"""

from __future__ import annotations

from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub_platform.products.models import (
    BillingPeriod,
    Offer,
    OfferFulfillmentType,
    OfferPaymentType,
    Price,
    Product,
)
from hub_platform.identity.models import Organization
from hub_platform.tenancy.context import TenantActorKind, TenantContext

VALID_FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)

# product_code -> list of offers; each offer carries its price rows (amount in rubles).
CATALOG: dict[str, list[dict]] = {
    "firepage": [
        {
            "code": "beautysoft",
            "name": "BeautySoft",
            "description": "Готовый сайт для студии красоты на CMS FirePage.",
            "fulfillment": OfferFulfillmentType.BOX_LICENSE,
            "payment": OfferPaymentType.ONE_TIME,
            "ai_offerable": True,
            "prices": [(BillingPeriod.ONE_TIME, 4900)],
        },
        {
            "code": "beautybarbiecore",
            "name": "BeautyBarbiecore",
            "description": "Готовый сайт салона красоты в стиле barbiecore.",
            "fulfillment": OfferFulfillmentType.BOX_LICENSE,
            "payment": OfferPaymentType.ONE_TIME,
            "ai_offerable": True,
            "prices": [(BillingPeriod.ONE_TIME, 4900)],
        },
        {
            "code": "beautytiffany",
            "name": "Beauty Tiffany",
            "description": "Готовый сайт салона красоты в палитре Tiffany.",
            "fulfillment": OfferFulfillmentType.BOX_LICENSE,
            "payment": OfferPaymentType.ONE_TIME,
            "ai_offerable": True,
            "prices": [(BillingPeriod.ONE_TIME, 4900)],
        },
    ],
    "foxray": [
        {
            "code": "free",
            "name": "Бесплатный",
            "description": "До 3 пациентов, все типы расчётов, PDF без брендирования, история.",
            "fulfillment": OfferFulfillmentType.SAAS_ACCESS,
            "payment": OfferPaymentType.SUBSCRIPTION,
            "ai_offerable": True,
            "prices": [(BillingPeriod.MONTH, 0)],
        },
        {
            "code": "pro",
            "name": "Про",
            "description": "Безлимит пациентов, брендирование клиники, приоритетная поддержка.",
            "fulfillment": OfferFulfillmentType.SAAS_ACCESS,
            "payment": OfferPaymentType.SUBSCRIPTION,
            "ai_offerable": True,
            "prices": [(BillingPeriod.MONTH, 4900), (BillingPeriod.YEAR, 47040)],
        },
        {
            "code": "max",
            "name": "Макс",
            "description": "Всё из Про, AI-расстановка точек, ранний доступ. Скоро.",
            "fulfillment": OfferFulfillmentType.SAAS_ACCESS,
            "payment": OfferPaymentType.SUBSCRIPTION,
            "ai_offerable": False,
            "is_active": False,
            "prices": [],
        },
    ],
}


class Command(BaseCommand):
    help = "Seed FirePage and Foxray catalog offers and prices (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True)

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        try:
            organization = Organization.objects.get(public_id=options["organization"])
        except (Organization.DoesNotExist, ValueError) as error:
            raise CommandError("Unknown organization public UUID") from error
        context = TenantContext.for_resource(
            organization, actor_kind=TenantActorKind.SYSTEM
        )
        created_offers = 0
        created_prices = 0
        for product_code, offers in CATALOG.items():
            product = Product.objects.filter(
                organization=context.organization,
                code=product_code,
            ).first()
            if product is None:
                self.stderr.write(f"product '{product_code}' not found — skipped")
                continue
            for spec in offers:
                offer, offer_new = Offer.objects.update_or_create(
                    product=product,
                    code=spec["code"],
                    defaults={
                        "name": spec["name"],
                        "description": spec["description"],
                        "fulfillment_type": spec["fulfillment"],
                        "payment_type": spec["payment"],
                        "fiscal_name": spec["name"],
                        "is_active": spec.get("is_active", True),
                        "ai_offerable": spec["ai_offerable"],
                    },
                )
                created_offers += int(offer_new)
                for billing_period, amount_rub in spec["prices"]:
                    _, price_new = Price.objects.update_or_create(
                        offer=offer,
                        currency="RUB",
                        billing_period=billing_period,
                        version=1,
                        defaults={
                            "amount_minor": amount_rub * 100,
                            "valid_from": VALID_FROM,
                            "is_active": True,
                        },
                    )
                    created_prices += int(price_new)
        self.stdout.write(
            self.style.SUCCESS(
                f"catalog seeded: +{created_offers} offers, +{created_prices} prices"
            )
        )
