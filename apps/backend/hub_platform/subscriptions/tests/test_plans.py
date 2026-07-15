from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import TestCase

from hub_platform.subscriptions.keys import PlanCode, QuotaKey
from hub_platform.subscriptions.models import Plan, PlanVersion, QuotaGrant
from hub_platform.subscriptions.plan_service import publish_plan_version


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
        self.assertFalse(
            startup.quota_grants.filter(
                definition__key__in=[
                    QuotaKey.MANAGED_AI_CREDITS,
                    QuotaKey.STORAGE_BYTES,
                    QuotaKey.CRM_API_REQUESTS_PER_WINDOW,
                ]
            ).exists()
        )

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
