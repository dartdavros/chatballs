"""Seed processing channels (M1.2a, ADR-HUB-0019). Idempotent.

Creates the company site channel "edevs" (no product) plus product channels for
FoxRay and FirePage, each with a live system prompt and the Sonnet 4.6 model,
bound to the configured OpenRouter provider integration if present.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from hub_platform.channels.models import DEFAULT_CHANNEL_MODEL, Channel
from hub_platform.identity.models import Department, Organization
from hub_platform.integrations.models import Integration, IntegrationProvider
from hub_platform.products.models import Product

EDEVS_PROMPT = (
    "Ты — AI-ассистент компании Edevs на её главном сайте. Отвечай на русском, кратко и по делу. "
    "Компания делает два продукта: FirePage — готовые нишевые сайты на собственной CMS (разовая лицензия), "
    "и FoxRay — сервис для ортодонтов по подписке (тарифы Бесплатный/Про/Макс). "
    "Помогай посетителю разобраться, какой продукт ему подходит, отвечай на вопросы о компании и продуктах. "
    "Ты не проводишь оплату и не оформляешь заказ — при готовности к покупке или сложном вопросе предложи передать оператору."
)
FOXRAY_PROMPT = (
    "Ты — AI sales-ассистент продукта FoxRay (сервис для ортодонтов, подписка: Бесплатный/Про/Макс). "
    "Отвечай на русском, кратко и по делу, помогай подобрать тариф и довести до покупки. "
    "Оплату и оформление не проводишь — при готовности предложи оператора или ссылку покупки продукта."
)
FIREPAGE_PROMPT = (
    "Ты — AI sales-ассистент продукта FirePage (готовые нишевые сайты, разовая лицензия). "
    "Отвечай на русском, кратко и по делу, помогай выбрать сайт и довести до покупки. "
    "Оплату и оформление не проводишь — при готовности предложи оператора или ссылку покупки продукта."
)

# (code, name, product_code|None, system_prompt)
CHANNELS = [
    ("edevs", "Edevs — главный сайт", None, EDEVS_PROMPT),
    ("foxray-sales", "FoxRay — продажи", "foxray", FOXRAY_PROMPT),
    ("firepage-sales", "FirePage — продажи", "firepage", FIREPAGE_PROMPT),
]


class Command(BaseCommand):
    help = "Seed processing channels (edevs, foxray, firepage)."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        organization = Organization.objects.first()
        if organization is None:
            self.stderr.write("no organization — run bootstrap_owner first")
            return
        sales = Department.objects.filter(organization=organization, code="sales").first()
        provider = (
            Integration.objects.filter(organization=organization, provider=IntegrationProvider.OPENROUTER)
            .exclude(secret="")
            .order_by("id")
            .first()
        )
        created = 0
        for code, name, product_code, prompt in CHANNELS:
            product = Product.objects.filter(organization=organization, code=product_code).first() if product_code else None
            _, was_created = Channel.objects.update_or_create(
                organization=organization,
                code=code,
                defaults={
                    "name": name,
                    "department": sales,
                    "product": product,
                    "provider_integration": provider,
                    "model": DEFAULT_CHANNEL_MODEL,
                    "system_prompt": prompt,
                    "is_active": True,
                },
            )
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"channels seeded: +{created} new (provider={'set' if provider else 'none'})"
            )
        )
