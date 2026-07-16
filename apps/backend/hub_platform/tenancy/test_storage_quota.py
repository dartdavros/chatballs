from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from hub_platform.identity.models import Organization
from hub_platform.subscriptions.errors import QuotaExceeded
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import (
    Plan,
    PlanVersion,
    QuotaDefinition,
    QuotaGrant,
    QuotaLimitSource,
    QuotaMode,
)
from hub_platform.subscriptions.subscription_models import (
    Subscription,
    SubscriptionStatus,
)
from hub_platform.subscriptions.usage_models import UsagePeriod, UsagePeriodStatus
from hub_platform.tenancy.models import OrganizationStorageUsage, StorageReservation
from hub_platform.tenancy.storage_quota import (
    finalize_storage,
    release_storage,
    reserve_storage,
)
from hub_platform.testing import system_tenant_context


def _setup_storage_quota(org, *, limit_bytes: int) -> None:
    plan, _ = Plan.objects.get_or_create(
        code="STARTUP", defaults={"name": "Startup", "saleable": True}
    )
    version = PlanVersion.objects.create(plan=plan, version=97, agent_unit_price_minor=0)
    quota, _ = QuotaDefinition.objects.get_or_create(
        key=QuotaKey.STORAGE_BYTES,
        defaults={"name": "Storage", "unit": "bytes"},
    )
    QuotaGrant.objects.create(
        plan_version=version,
        definition=quota,
        mode=QuotaMode.HARD,
        limit_source=QuotaLimitSource.FIXED,
        limit_value=limit_bytes,
    )
    version.published_at = timezone.now()
    version.save(update_fields=["published_at"])
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
    UsagePeriod.objects.update_or_create(
        organization=org,
        subscription=org.subscription,
        status=UsagePeriodStatus.OPEN,
        defaults={
            "starts_at": timezone.now(),
            "ends_at": timezone.now() + timedelta(days=30),
        },
    )


class StorageReserveFinalizeReleaseTests(TestCase):
    """SPEC-HUB-0022 §10: storage_bytes reserve/finalize/release lifecycle."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Stor", slug="stor")
        _setup_storage_quota(self.organization, limit_bytes=1000)
        self.context = system_tenant_context(self.organization)

    def _usage(self) -> OrganizationStorageUsage:
        # refresh_from_db: the service mutates rows via F-expressions, so the cached
        # Python value can hold a CombinedExpression instead of the persisted int.
        self.organization.storage_usage.refresh_from_db()
        return self.organization.storage_usage

    def test_reserve_blocks_reserved_bytes_against_quota(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=700, idempotency_key="up:1"
        )
        # 700 reserved out of 1000 -> another 400 must be denied (700+400 > 1000).
        with self.assertRaises(QuotaExceeded):
            reserve_storage(
                context=self.context, expected_bytes=400, idempotency_key="up:2"
            )
        # 300 still fits exactly.
        reserve_storage(
            context=self.context, expected_bytes=300, idempotency_key="up:3"
        )
        self.assertEqual(self._usage().reserved_bytes, 1000)
        self.assertEqual(self._usage().bytes_used, 0)

    def test_reserve_is_idempotent_on_replay(self) -> None:
        first = reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:replay"
        )
        second = reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:replay"
        )
        self.assertEqual(first.id, second.id)
        # A replay must not double-count the reservation.
        self.assertEqual(self._usage().reserved_bytes, 500)

    def test_finalize_moves_reserved_into_used(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:1"
        )
        finalize_storage(
            context=self.context, idempotency_key="up:1", actual_bytes=400
        )
        self.assertEqual(self._usage().reserved_bytes, 0)
        self.assertEqual(self._usage().bytes_used, 400)

    def test_finalize_overrun_consumes_extra_within_quota(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:1"
        )
        # Actual size exceeded the estimate but still fits (500 + 400 overrun = 900).
        finalize_storage(
            context=self.context, idempotency_key="up:1", actual_bytes=900
        )
        self.assertEqual(self._usage().bytes_used, 900)

    def test_finalize_overrun_beyond_quota_raises(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:1"
        )
        with self.assertRaises(QuotaExceeded):
            finalize_storage(
                context=self.context, idempotency_key="up:1", actual_bytes=1001
            )
        # Reservation untouched when finalize refused.
        self.assertEqual(self._usage().reserved_bytes, 500)

    def test_release_returns_reserved_bytes_on_failure(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=600, idempotency_key="up:1"
        )
        release_storage(context=self.context, idempotency_key="up:1")
        self.assertEqual(self._usage().reserved_bytes, 0)
        self.assertEqual(self._usage().bytes_used, 0)
        # Capacity is available again after release.
        reserve_storage(
            context=self.context, expected_bytes=600, idempotency_key="up:2"
        )

    def test_release_and_finalize_are_idempotent_when_missing(self) -> None:
        # No active reservation -> no-op, no raise.
        release_storage(context=self.context, idempotency_key="never")
        finalize_storage(
            context=self.context, idempotency_key="never", actual_bytes=100
        )

    def test_finalize_then_release_is_noop(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:1"
        )
        finalize_storage(
            context=self.context, idempotency_key="up:1", actual_bytes=500
        )
        release_storage(context=self.context, idempotency_key="up:1")
        # Finalized reservation must not be released retroactively.
        self.assertEqual(self._usage().bytes_used, 500)
        self.assertEqual(self._usage().reserved_bytes, 0)

    def test_reservation_records_are_persisted(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:1"
        )
        reservation = StorageReservation.objects.get(idempotency_key="up:1")
        self.assertEqual(reservation.reserved_bytes, 500)
        self.assertFalse(reservation.finalized)
        self.assertFalse(reservation.released)
