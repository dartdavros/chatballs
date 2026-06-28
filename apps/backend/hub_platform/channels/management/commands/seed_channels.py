"""Seed processing channels (M1.2a, ADR-HUB-0019). Idempotent.

Creates the company site channel "edevs" (no product) plus product channels for
FoxRay and FirePage, each with a live system prompt and the Sonnet 4.6 model,
bound to the configured OpenRouter provider integration if present.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from hub_platform.ai import releases as release_service
from hub_platform.ai.models import AIAgent
from hub_platform.ai.services import AgentCreateInput, create_agent
from hub_platform.channels.models import DEFAULT_CHANNEL_MODEL, Channel
from hub_platform.identity.models import Department, Organization
from hub_platform.integrations.models import Integration, IntegrationProvider
from hub_platform.products.models import Product

# Общий стиль для мессенджера: простой текст без markdown и сдержанная передача оператору.
STYLE = (
    " Пиши простым текстом для мессенджера: без markdown-разметки (никаких **, ##, маркированных "
    "списков и разделителей ---), короткими абзацами, на русском, по делу. "
    "Не предлагай оператора по умолчанию: передавай человеку только если клиент сам просит человека, "
    "вопрос выходит за рамки твоих знаний, или это жалоба/спорная ситуация."
)
EDEVS_PROMPT = (
    "Ты — AI-ассистент компании Edevs на её главном сайте. "
    "Компания делает два продукта: FirePage — готовые нишевые сайты на собственной CMS (разовая лицензия), "
    "и FoxRay — сервис для ортодонтов по подписке (тарифы Бесплатный/Про/Макс). "
    "Помогай посетителю разобраться, какой продукт ему подходит, отвечай на вопросы о компании и продуктах. "
    "Оплату и оформление ты не проводишь." + STYLE
)
FOXRAY_PROMPT = (
    "Ты — AI sales-ассистент продукта FoxRay (сервис для ортодонтов, подписка: Бесплатный/Про/Макс). "
    "Помогай подобрать тариф и ответить на вопросы. Оплату и оформление не проводишь." + STYLE
)
FIREPAGE_PROMPT = (
    "Ты — AI sales-ассистент продукта FirePage (готовые нишевые сайты, разовая лицензия). "
    "Помогай выбрать сайт и ответить на вопросы. Оплату и оформление не проводишь." + STYLE
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
        owner = organization.employees.filter(role="OWNER").first()
        author = owner.user if owner else None
        created = 0
        agents_created = 0
        for code, name, product_code, prompt in CHANNELS:
            product = Product.objects.filter(organization=organization, code=product_code).first() if product_code else None
            channel, was_created = Channel.objects.update_or_create(
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
            # Агент канала + опубликованный релиз (ADR-HUB-0007/0019).
            if not AIAgent.objects.filter(channel=channel).exists():
                agent, release = create_agent(
                    organization=organization,
                    author=author,
                    data=AgentCreateInput(
                        channel_code=code,
                        model=DEFAULT_CHANNEL_MODEL,
                        system_prompt=prompt,
                        knowledge_document_ids=[],
                    ),
                )
                release_service.publish_release(release=release)
                agent.is_active = True
                agent.save(update_fields=["is_active", "updated_at"])
                agents_created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"channels seeded: +{created} channels, +{agents_created} agents (provider={'set' if provider else 'none'})"
            )
        )
