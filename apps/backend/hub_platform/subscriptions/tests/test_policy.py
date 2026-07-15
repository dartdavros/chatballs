from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from hub_platform.identity.models import HumanUser, Organization
from hub_platform.subscriptions.keys import EntitlementKey, QuotaKey
from hub_platform.subscriptions.models import OverrideOperation, OverrideTarget, QuotaMode
from hub_platform.subscriptions.override_service import create_override
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.testing import system_tenant_context


class EffectivePolicyTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Policy", slug="policy")
        self.actor = HumanUser.objects.create_user(email="platform-policy@example.test")
        self.context = system_tenant_context(self.organization)
        self.subscription = create_test_subscription(self.organization, quantity=2)

    def test_policy_uses_grants_quantity_and_active_overrides(self) -> None:
        create_override(
            context=self.context,
            created_by=self.actor,
            target=OverrideTarget.ENTITLEMENT,
            key=EntitlementKey.P2P_CALLS,
            operation=OverrideOperation.DISABLE,
            reason="Pilot restriction",
        )
        create_override(
            context=self.context,
            created_by=self.actor,
            target=OverrideTarget.QUOTA,
            key=QuotaKey.AI_AGENT_SLOTS,
            operation=OverrideOperation.ADD,
            value=1,
            reason="Temporary pilot slot",
        )
        create_override(
            context=self.context,
            created_by=self.actor,
            target=OverrideTarget.ENTITLEMENT,
            key=EntitlementKey.P2P_CALLS,
            operation=OverrideOperation.ENABLE,
            reason="Expired override",
            starts_at=timezone.now() - timedelta(days=2),
            ends_at=timezone.now() - timedelta(days=1),
        )
        create_override(
            context=self.context,
            created_by=self.actor,
            target=OverrideTarget.QUOTA,
            key=QuotaKey.PRODUCTS,
            operation=OverrideOperation.SET,
            value=2,
            reason="Temporary product cap",
        )

        policy = get_effective_policy(self.context)
        self.assertEqual(self.subscription.monthly_charge_minor, 580_000)
        self.assertFalse(policy.has_entitlement(EntitlementKey.P2P_CALLS))
        self.assertEqual(policy.quota(QuotaKey.AI_AGENT_SLOTS).limit, 3)
        self.assertEqual(policy.quota(QuotaKey.PRODUCTS).mode, QuotaMode.HARD)
        self.assertEqual(policy.quota(QuotaKey.PRODUCTS).limit, 2)
