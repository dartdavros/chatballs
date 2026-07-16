from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from hub_platform.subscriptions.errors import QuotaExceeded
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import (
    EntitlementDefinition,
    EntitlementGrant,
    Plan,
    PlanVersion,
    QuotaDefinition,
    QuotaGrant,
    QuotaLimitSource,
    QuotaMode,
)
from hub_platform.subscriptions.reservation_service import (
    expire_stale_reservations,
    release_usage,
    reserve_usage,
)
from hub_platform.subscriptions.usage_models import UsageCounter
from hub_platform.subscriptions.usage_service import record_usage
from hub_platform.testing import system_tenant_context
from hub_platform.identity.models import Organization


def _setup_concurrent_quota(org, *, limit: int) -> None:
    plan, _ = Plan.objects.get_or_create(code="STARTUP", defaults={"name": "Startup", "saleable": True})
    version = PlanVersion.objects.create(plan=plan, version=99, agent_unit_price_minor=0)
    quota, _ = QuotaDefinition.objects.get_or_create(
        key=QuotaKey.CONCURRENT_P2P_CALLS,
        defaults={"name": "P2P", "unit": "calls"},
    )
    QuotaGrant.objects.create(
        plan_version=version, definition=quota, mode=QuotaMode.CONCURRENT,
        limit_source=QuotaLimitSource.FIXED, limit_value=limit,
    )
    ent, _ = EntitlementDefinition.objects.get_or_create(key="p2p_calls", defaults={"name": "P2P"})
    EntitlementGrant.objects.create(plan_version=version, definition=ent)
    # Publish so policy sees it.
    version.published_at = timezone.now()
    version.save(update_fields=["published_at"])
    from hub_platform.subscriptions.subscription_models import Subscription, SubscriptionStatus
    Subscription.objects.update_or_create(
        organization=org,
        defaults={
            "plan_version": version,
            "ai_agent_quantity": 1,
            "status": SubscriptionStatus.ACTIVE,
            "current_period_start": timezone.now(),
            "current_period_end": timezone.now() + timedelta(days=30),
        },
    )
    from hub_platform.subscriptions.usage_models import UsagePeriod, UsagePeriodStatus
    UsagePeriod.objects.update_or_create(
        organization=org,
        subscription=org.subscription,
        status=UsagePeriodStatus.OPEN,
        defaults={"starts_at": timezone.now(), "ends_at": timezone.now() + timedelta(days=30)},
    )


class ReservationTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Resv", slug="resv")
        _setup_concurrent_quota(self.organization, limit=2)
        self.context = system_tenant_context(self.organization)

    def test_reserve_release_lifecycle(self) -> None:
        result = reserve_usage(
            context=self.context,
            quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
            idempotency_key="p2p:1",
            lease_seconds=3600,
            source="test",
            aggregate_type="CallSession",
            aggregate_id="1",
        )
        self.assertEqual(result.reserved_value, 1)
        release_usage(context=self.context, idempotency_key="p2p:1")
        counter = UsageCounter.objects.get(
            organization=self.organization,
            quota_definition__key=QuotaKey.CONCURRENT_P2P_CALLS,
        )
        self.assertEqual(counter.reserved_value, 0)

    def test_reserve_replay_is_idempotent(self) -> None:
        first = reserve_usage(
            context=self.context, quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
            idempotency_key="p2p:replay", lease_seconds=3600, source="test",
        )
        second = reserve_usage(
            context=self.context, quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
            idempotency_key="p2p:replay", lease_seconds=3600, source="test",
        )
        self.assertEqual(first.reservation.id, second.reservation.id)
        self.assertEqual(second.reserved_value, 1)

    def test_quota_exceeded_when_limit_reached(self) -> None:
        for i in range(2):
            reserve_usage(
                context=self.context, quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
                idempotency_key=f"p2p:{i}", lease_seconds=3600, source="test",
            )
        with self.assertRaises(QuotaExceeded):
            reserve_usage(
                context=self.context, quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
                idempotency_key="p2p:third", lease_seconds=3600, source="test",
            )

    def test_release_missing_reservation_is_noop(self) -> None:
        # Idempotent release of a never-reserved key must not raise.
        release_usage(context=self.context, idempotency_key="p2p:never")

    def test_expire_stale_releases_lapsed_leases(self) -> None:
        reserve_usage(
            context=self.context, quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
            idempotency_key="p2p:stale", lease_seconds=1, source="test",
        )
        # Force the lease into the past.
        from hub_platform.subscriptions.models import UsageReservation
        UsageReservation.objects.filter(idempotency_key="p2p:stale").update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        expired = expire_stale_reservations()
        self.assertEqual(expired, 1)
        counter = UsageCounter.objects.get(
            organization=self.organization,
            quota_definition__key=QuotaKey.CONCURRENT_P2P_CALLS,
        )
        self.assertEqual(counter.reserved_value, 0)
