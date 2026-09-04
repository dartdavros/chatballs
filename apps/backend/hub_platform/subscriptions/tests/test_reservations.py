from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
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
from hub_platform.testing import system_tenant_context


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


def _setup_membership_quota(org) -> None:
    """Concurrent p2p quota whose limit derives from the active non-OWNER
    membership count (C07 MEMBERSHIP_COUNT)."""
    plan, _ = Plan.objects.get_or_create(
        code="STARTUP", defaults={"name": "Startup", "saleable": True}
    )
    version = PlanVersion.objects.create(plan=plan, version=98, agent_unit_price_minor=0)
    quota, _ = QuotaDefinition.objects.get_or_create(
        key=QuotaKey.CONCURRENT_P2P_CALLS,
        defaults={"name": "P2P", "unit": "calls"},
    )
    QuotaGrant.objects.create(
        plan_version=version,
        definition=quota,
        mode=QuotaMode.CONCURRENT,
        limit_source=QuotaLimitSource.MEMBERSHIP_COUNT,
        limit_value=None,
    )
    ent, _ = EntitlementDefinition.objects.get_or_create(
        key="p2p_calls", defaults={"name": "P2P"}
    )
    EntitlementGrant.objects.create(plan_version=version, definition=ent)
    version.published_at = timezone.now()
    version.save(update_fields=["published_at"])
    from hub_platform.subscriptions.subscription_models import (
        Subscription,
        SubscriptionStatus,
    )

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
    from hub_platform.subscriptions.usage_models import (
        UsagePeriod,
        UsagePeriodStatus,
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


def _make_member(org, *, email: str, role: str = EmployeeRole.EMPLOYEE) -> None:
    user = HumanUser.objects.create_user(email=email, password="member-password")
    OrganizationMembership.objects.create(
        user=user,
        organization=org,
        role=role,
        position_title="Member",
    )


class MembershipCountLimitTests(TestCase):
    """C07 MEMBERSHIP_COUNT: concurrent_p2p_calls limit equals the count of active,
    non-OWNER memberships (PLAN-CUSTOCRM-0003 §12). OWNER and blocked members do not
    count toward the limit."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="MemOrg", slug="memorg")
        _setup_membership_quota(self.organization)
        self.context = system_tenant_context(self.organization)

    def test_limit_is_zero_without_active_non_owner_members(self) -> None:
        # Only an OWNER exists; it does not count -> limit 0 -> reservation denied.
        owner = HumanUser.objects.create_user(
            email="owner@memorg.tech", password="owner-password-123"
        )
        OrganizationMembership.objects.create(
            user=owner,
            organization=self.organization,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )
        with self.assertRaises(QuotaExceeded):
            reserve_usage(
                context=self.context,
                quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
                idempotency_key="p2p:1",
                lease_seconds=3600,
                source="test",
            )

    def test_limit_grows_with_added_non_owner_member(self) -> None:
        _make_member(self.organization, email="e1@memorg.tech")
        # One slot available -> first reserve succeeds, second is denied.
        reserve_usage(
            context=self.context,
            quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
            idempotency_key="p2p:a",
            lease_seconds=3600,
            source="test",
        )
        with self.assertRaises(QuotaExceeded):
            reserve_usage(
                context=self.context,
                quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
                idempotency_key="p2p:b",
                lease_seconds=3600,
                source="test",
            )
        # Adding a second member opens a second slot.
        _make_member(self.organization, email="e2@memorg.tech")
        reserve_usage(
            context=self.context,
            quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
            idempotency_key="p2p:c",
            lease_seconds=3600,
            source="test",
        )

    def test_blocked_member_does_not_count(self) -> None:
        member = _make_member(self.organization, email="blocked@memorg.tech")
        # Block the only non-OWNER member -> no slots -> reservation denied.
        OrganizationMembership.objects.filter(
            user__email="blocked@memorg.tech"
        ).update(blocked_at=timezone.now())
        del member
        with self.assertRaises(QuotaExceeded):
            reserve_usage(
                context=self.context,
                quota_key=QuotaKey.CONCURRENT_P2P_CALLS,
                idempotency_key="p2p:1",
                lease_seconds=3600,
                source="test",
            )
