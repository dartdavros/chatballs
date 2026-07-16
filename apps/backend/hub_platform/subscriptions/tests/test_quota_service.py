from __future__ import annotations

from django.test import TestCase

from hub_platform.identity.models import Organization
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.quota_service import check
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.subscriptions.usage_service import record_usage
from hub_platform.testing import system_tenant_context


class QuotaServiceCheckTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Check", slug="check")
        self.context = system_tenant_context(self.organization)
        # ai_agent_slots limit = quantity = 2 (SUBSCRIPTION_AI_AGENT_QUANTITY).
        create_test_subscription(self.organization, quantity=2)

    def test_unlimited_returns_true(self) -> None:
        # products is UNLIMITED in the test STARTUP plan -> always fits.
        self.assertTrue(check(self.context, QuotaKey.PRODUCTS, quantity=999))

    def test_within_limit_returns_true(self) -> None:
        self.assertTrue(check(self.context, QuotaKey.AI_AGENT_SLOTS, quantity=1))

    def test_over_limit_returns_false(self) -> None:
        # Consume both slots first, then check a third.
        record_usage(
            context=self.context, quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=2, idempotency_key="slot-1", source="test",
        )
        self.assertFalse(check(self.context, QuotaKey.AI_AGENT_SLOTS, quantity=1))

    def test_no_policy_returns_false(self) -> None:
        bare = Organization.objects.create(name="Bare", slug="bare")
        self.assertFalse(check(system_tenant_context(bare), QuotaKey.AI_AGENT_SLOTS))
