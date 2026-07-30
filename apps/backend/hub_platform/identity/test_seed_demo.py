from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from hub_platform.ai.models import AIAgent, Knowledge, KnowledgeAttachment
from hub_platform.calls.models import CallSession
from hub_platform.conversations.models import Conversation, Message
from hub_platform.identity.demo_seed.orchestrator import DemoRefs, run_demo_seed
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
)
from hub_platform.notifications.models import Notification
from hub_platform.orders.models import Order
from hub_platform.products.models import Offer, Price, Product
from hub_platform.sales.models import Sale, SaleEvent
from hub_platform.support.models import ProductSupportContract, SupportIdentitySnapshot
from hub_platform.support_portals.models import PortalArticle, SupportPortal
from hub_platform.tenancy.context import TenantActorKind, TenantContext
from hub_platform.tenancy.database import tenant_atomic

DEMO_SLUG = "severnaya-verf"


def _run_seed() -> DemoRefs:
    organization = Organization.objects.get(slug=DEMO_SLUG)
    context = TenantContext.for_resource(organization, actor_kind=TenantActorKind.SYSTEM)
    with tenant_atomic(context):
        return run_demo_seed(context)


class SeedDemoTests(TestCase):
    """Покрывает создание, идемпотентность и dry-run демо-сида «Северная Верфь»."""

    def setUp(self) -> None:
        # Организация создаётся командой; здесь нужен только shell для контекста.
        Organization.objects.create(name="Северная Верфь", slug=DEMO_SLUG)

    def test_creates_full_dataset(self) -> None:
        refs = _run_seed()

        self.assertEqual(refs.organization.slug, DEMO_SLUG)
        # Персонал: владелец, админ, 2 продажи, 2 поддержки.
        self.assertEqual(refs.organization.memberships.count(), 6)
        self.assertEqual(
            refs.organization.memberships.filter(role=EmployeeRole.EMPLOYEE).count(), 4
        )
        # Продукты, офферы, цены.
        self.assertEqual(Product.objects.filter(organization=refs.organization).count(), 2)
        self.assertGreaterEqual(
            Offer.objects.filter(product__organization=refs.organization).count(), 3
        )
        self.assertGreaterEqual(Price.objects.count(), 3)
        # Каналы и AI-агенты.
        self.assertGreaterEqual(refs.organization.channels.count(), 6)
        self.assertGreaterEqual(AIAgent.objects.count(), 3)
        # База знаний со вложениями.
        self.assertGreaterEqual(Knowledge.objects.filter(organization=refs.organization).count(), 4)
        self.assertGreaterEqual(KnowledgeAttachment.objects.count(), 2)
        # Диалоги и сообщения.
        conversations = Conversation.objects.filter(organization=refs.organization)
        self.assertGreaterEqual(conversations.count(), 8)
        self.assertGreaterEqual(Message.objects.count(), 10)
        # Заказы и продажи.
        self.assertGreaterEqual(Order.objects.filter(organization=refs.organization).count(), 3)
        self.assertGreaterEqual(Sale.objects.count(), 1)
        self.assertGreaterEqual(SaleEvent.objects.count(), 1)
        # Поддержка: контракты, снимки, портал со статьями.
        self.assertGreaterEqual(ProductSupportContract.objects.count(), 2)
        self.assertGreaterEqual(SupportIdentitySnapshot.objects.count(), 2)
        self.assertGreaterEqual(PortalArticle.objects.count(), 6)
        self.assertEqual(SupportPortal.objects.count(), 1)
        # Операции: звонки и уведомления.
        self.assertGreaterEqual(CallSession.objects.count(), 1)
        self.assertGreaterEqual(Notification.objects.count(), 3)

    def test_idempotent_rerun(self) -> None:
        _run_seed()
        counts_before = {
            "users": HumanUser.objects.filter(email__icontains="severnayaverf.ru").count(),
            "products": Product.objects.filter(organization__slug=DEMO_SLUG).count(),
            "conversations": Conversation.objects.filter(organization__slug=DEMO_SLUG).count(),
            "messages": Message.objects.filter(conversation__organization__slug=DEMO_SLUG).count(),
            "orders": Order.objects.filter(organization__slug=DEMO_SLUG).count(),
        }
        _run_seed()
        counts_after = {
            "users": HumanUser.objects.filter(email__icontains="severnayaverf.ru").count(),
            "products": Product.objects.filter(organization__slug=DEMO_SLUG).count(),
            "conversations": Conversation.objects.filter(organization__slug=DEMO_SLUG).count(),
            "messages": Message.objects.filter(conversation__organization__slug=DEMO_SLUG).count(),
            "orders": Order.objects.filter(organization__slug=DEMO_SLUG).count(),
        }
        self.assertEqual(counts_before, counts_after)

    @override_settings(DEBUG=True)
    def test_dry_run_creates_nothing(self) -> None:
        before = Conversation.objects.filter(organization__slug=DEMO_SLUG).count()
        out = StringIO()
        call_command("seed_demo", stdout=out)
        after = Conversation.objects.filter(organization__slug=DEMO_SLUG).count()
        self.assertEqual(before, after)
        self.assertIn("Dry-run", out.getvalue())
