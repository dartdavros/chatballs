from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import TestCase

from hub_platform.subscriptions.keys import PlanCode, QuotaKey
from hub_platform.subscriptions.models import Plan, PlanVersion, QuotaGrant
from hub_platform.subscriptions.plan_service import publish_plan_version

_MIB = 1024 * 1024
_GIB = 1024 * 1024 * 1024


class PlanVersionTests(TestCase):
    def test_canonical_plan_drafts_are_seeded_without_unapproved_limits(self) -> None:
        plans = {plan.code: plan for plan in Plan.objects.all()}
        self.assertEqual(set(plans), set(PlanCode.values))
        self.assertTrue(plans[PlanCode.FREE].saleable)
        self.assertTrue(plans[PlanCode.STARTUP].saleable)
        self.assertFalse(plans[PlanCode.BUSINESS].saleable)
        self.assertFalse(plans[PlanCode.CORPORATION].saleable)

        free = plans[PlanCode.FREE].versions.get(version=1)
        startup = plans[PlanCode.STARTUP].versions.get(version=1)
        self.assertEqual(free.agent_unit_price_minor, 0)
        self.assertEqual(free.fixed_ai_agent_quantity, 1)
        self.assertEqual(startup.agent_unit_price_minor, 290_000)
        self.assertIsNone(free.published_at)
        self.assertIsNone(startup.published_at)

    def test_free_startup_approved_quota_grants(self) -> None:
        # Owner-approved quota values (2026-07-15) required to publish Free/Startup
        # before C06. Business/Corporation stay draft with only ai_agent_slots.
        free = PlanVersion.objects.get(plan__code=PlanCode.FREE, version=1)
        startup = PlanVersion.objects.get(plan__code=PlanCode.STARTUP, version=1)
        business = PlanVersion.objects.get(plan__code=PlanCode.BUSINESS, version=1)
        corporation = PlanVersion.objects.get(plan__code=PlanCode.CORPORATION, version=1)

        free_quotas = self._quota_map(free)
        self.assertEqual(free_quotas[QuotaKey.MANAGED_AI_CREDITS], ("HARD", 300, None))
        self.assertEqual(
            free_quotas[QuotaKey.STORAGE_BYTES], ("HARD", 500 * _MIB, None)
        )
        self.assertEqual(
            free_quotas[QuotaKey.CRM_API_REQUESTS_PER_WINDOW], ("HARD", 0, None)
        )
        self.assertEqual(
            free_quotas[QuotaKey.CONCURRENT_P2P_CALLS], ("CONCURRENT", 0, None)
        )
        self.assertEqual(
            free_quotas[QuotaKey.CONCURRENT_VOICE_SESSIONS], ("CONCURRENT", 0, None)
        )

        startup_quotas = self._quota_map(startup)
        self.assertEqual(
            startup_quotas[QuotaKey.MANAGED_AI_CREDITS], ("HARD", 1000, None)
        )
        self.assertEqual(
            startup_quotas[QuotaKey.STORAGE_BYTES], ("HARD", 2 * _GIB, None)
        )
        self.assertEqual(
            startup_quotas[QuotaKey.CRM_API_REQUESTS_PER_WINDOW], ("RATE", 60, 60)
        )
        # C07: STARTUP concurrent_p2p_calls derives from the active non-OWNER
        # membership count (migration 0005), so limit_value is NULL.
        self.assertEqual(
            startup_quotas[QuotaKey.CONCURRENT_P2P_CALLS], ("CONCURRENT", None, None)
        )
        self.assertEqual(
            startup_quotas[QuotaKey.CONCURRENT_VOICE_SESSIONS],
            ("CONCURRENT", 10, None),
        )

        # BUSINESS received the owner-approved Managed AI pool in migration 0006.
        business_quotas = self._quota_map(business)
        self.assertEqual(
            business_quotas[QuotaKey.MANAGED_AI_CREDITS], ("HARD", 3000, None)
        )
        self.assertEqual(
            set(business_quotas),
            {QuotaKey.AI_AGENT_SLOTS, QuotaKey.MANAGED_AI_CREDITS},
        )
        # CORPORATION remains contract-specific and has no numeric credits grant.
        self.assertEqual(set(self._quota_map(corporation)), {QuotaKey.AI_AGENT_SLOTS})

    def test_business_has_3000_managed_credits(self) -> None:
        business = PlanVersion.objects.get(plan__code=PlanCode.BUSINESS, version=1)
        grant = business.quota_grants.get(definition__key=QuotaKey.MANAGED_AI_CREDITS)
        self.assertEqual(grant.mode, "HARD")
        self.assertEqual(grant.limit_source, "FIXED")
        self.assertEqual(grant.limit_value, 3000)

    @staticmethod
    def _quota_map(version: PlanVersion) -> dict[str, tuple[str, int | None, int | None]]:
        return {
            grant.definition.key: (grant.mode, grant.limit_value, grant.window_seconds)
            for grant in version.quota_grants.all()
        }

    def test_published_version_and_grants_are_immutable(self) -> None:
        version = publish_plan_version(
            PlanVersion.objects.get(plan__code=PlanCode.STARTUP, version=1)
        )
        version.agent_unit_price_minor = 1
        with self.assertRaises(ValidationError):
            version.save()
        grant = version.quota_grants.get(definition__key=QuotaKey.AI_AGENT_SLOTS)
        grant.limit_value = 99
        with self.assertRaises(ValidationError):
            grant.save()

        with self.assertRaises(DatabaseError), transaction.atomic():
            PlanVersion.objects.filter(pk=version.pk).update(agent_unit_price_minor=1)
        with self.assertRaises(DatabaseError), transaction.atomic():
            QuotaGrant.objects.filter(pk=grant.pk).update(mode="UNLIMITED")
