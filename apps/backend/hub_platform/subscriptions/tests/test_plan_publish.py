from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase

from hub_platform.subscriptions.keys import PlanCode
from hub_platform.subscriptions.models import PlanVersion
from hub_platform.subscriptions.plan_publish_service import (
    publish_saleable_plan_versions,
)


class PublishSaleablePlanVersionsTests(TestCase):
    def test_publishes_free_and_startup_and_is_idempotent(self) -> None:
        first = publish_saleable_plan_versions()
        codes = {r.plan_code for r in first}
        self.assertEqual(codes, {PlanCode.FREE, PlanCode.STARTUP})
        self.assertTrue(all(r.published for r in first))
        for code in (PlanCode.FREE, PlanCode.STARTUP):
            version = PlanVersion.objects.get(plan__code=code, version=1)
            self.assertIsNotNone(version.published_at)

        # Idempotent: running again reports already_published, no error.
        second = publish_saleable_plan_versions()
        self.assertTrue(all(r.already_published for r in second))
        self.assertFalse(any(r.published for r in second))

    def test_business_and_corporation_are_not_published(self) -> None:
        publish_saleable_plan_versions()
        for code in (PlanCode.BUSINESS, PlanCode.CORPORATION):
            version = PlanVersion.objects.get(plan__code=code, version=1)
            self.assertIsNone(version.published_at)


class PublishPlanVersionsCommandTests(TestCase):
    def test_command_publishes_saleable_plans(self) -> None:
        call_command("publish_plan_versions")
        for code in (PlanCode.FREE, PlanCode.STARTUP):
            version = PlanVersion.objects.get(plan__code=code, version=1)
            self.assertIsNotNone(version.published_at)

    def test_command_is_idempotent(self) -> None:
        call_command("publish_plan_versions")
        # Second invocation must not raise.
        call_command("publish_plan_versions")
