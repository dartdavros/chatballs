"""Seed processing channels (ADR-HUB-0019/0023). Idempotent.

Creates the company site channel "edevs" (no product) plus product channels for
FoxRay and FirePage, each with a draft AI agent (persona/tone/instructions),
bound to the configured OpenRouter provider integration if present.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from hub_platform.ai.models import DEFAULT_AI_MODEL, AIAgent, AIAgentStatus
from hub_platform.channels.models import Channel
from hub_platform.identity.models import Department, Organization
from hub_platform.integrations.models import Integration, IntegrationProvider
from hub_platform.products.models import Product
from hub_platform.tenancy.context import TenantActorKind, TenantContext
from hub_platform.tenancy.database import set_local_tenant

# Тон общения (поле tone агента): простой текст для мессенджера.
TONE = (
    "Пиши простым текстом для мессенджера: без markdown-разметки (никаких **, ##, маркированных "
    "списков и разделителей ---), короткими абзацами, на русском, по делу. "
    "Не предлагай оператора по умолчанию: передавай человеку только если клиент сам просит человека, "
    "вопрос выходит за рамки твоих знаний, или это жалоба/спорная ситуация."
)
EDEVS_PERSONA = (
    "Ты — AI-ассистент компании Edevs на её главном сайте. "
    "Компания делает два продукта: FirePage — готовые нишевые сайты на собственной CMS (разовая лицензия), "
    "и FoxRay — сервис для ортодонтов по подписке (тарифы Бесплатный/Про/Макс)."
)
EDEVS_INSTRUCTIONS = (
    "Помогай посетителю разобраться, какой продукт ему подходит, отвечай на вопросы о компании и продуктах. "
    "Оплату и оформление ты не проводишь."
)
FOXRAY_PERSONA = "Ты — AI sales-ассистент продукта FoxRay (сервис для ортодонтов, подписка: Бесплатный/Про/Макс)."
FOXRAY_INSTRUCTIONS = "Помогай подобрать тариф и ответить на вопросы. Оплату и оформление не проводишь."
FIREPAGE_PERSONA = "Ты — AI sales-ассистент продукта FirePage (готовые нишевые сайты, разовая лицензия)."
FIREPAGE_INSTRUCTIONS = "Помогай выбрать сайт и ответить на вопросы. Оплату и оформление не проводишь."

# (code, name, product_code|None, persona, instructions)
CHANNELS = [
    ("edevs", "Edevs — главный сайт", None, EDEVS_PERSONA, EDEVS_INSTRUCTIONS),
    ("foxray-sales", "FoxRay — продажи", "foxray", FOXRAY_PERSONA, FOXRAY_INSTRUCTIONS),
    ("firepage-sales", "FirePage — продажи", "firepage", FIREPAGE_PERSONA, FIREPAGE_INSTRUCTIONS),
]


class Command(BaseCommand):
    help = "Seed processing channels (edevs, foxray, firepage)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="Organization public UUID")

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        try:
            organization = Organization.objects.get(public_id=options["organization"])
        except (Organization.DoesNotExist, ValueError):
            self.stderr.write("organization not found")
            return
        context = TenantContext.for_resource(
            organization,
            actor_kind=TenantActorKind.SYSTEM,
        )
        set_local_tenant(context)
        sales = Department.objects.filter(organization=organization, code="sales").first()
        provider = (
            Integration.objects.filter(organization=organization, provider=IntegrationProvider.OPENROUTER)
            .exclude(secret="")
            .order_by("id")
            .first()
        )
        created = 0
        agents_created = 0
        for code, name, product_code, persona, instructions in CHANNELS:
            product = Product.objects.filter(organization=organization, code=product_code).first() if product_code else None
            channel, was_created = Channel.objects.update_or_create(
                organization=organization,
                code=code,
                defaults={
                    "name": name,
                    "department": sales,
                    "product": product,
                    "provider_integration": provider,
                    "is_active": True,
                },
            )
            created += int(was_created)
            # Агент канала (ADR-HUB-0023): одна сущность, без релизов.
            if not AIAgent.objects.filter(channel=channel).exists():
                AIAgent.objects.create(
                    organization=organization,
                    channel=channel,
                    name=f"{name} Agent",
                    status=AIAgentStatus.DRAFT,
                    model=DEFAULT_AI_MODEL,
                    persona=persona,
                    tone=TONE,
                    instructions=instructions,
                )
                agents_created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"channels seeded: +{created} channels, +{agents_created} agents (provider={'set' if provider else 'none'})"
            )
        )
