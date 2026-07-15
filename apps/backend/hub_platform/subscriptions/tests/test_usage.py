from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import TestCase

from hub_platform.identity.models import Organization
from hub_platform.subscriptions.errors import QuotaExceeded
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import UsageCounter, UsageLedgerEntry
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.subscriptions.usage_service import (
    rebuild_counter,
    record_adjustment,
    record_usage,
)
from hub_platform.testing import system_tenant_context


class UsageAccountingTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Usage", slug="usage")
        self.context = system_tenant_context(self.organization)
        create_test_subscription(self.organization, quantity=2)

    def test_consume_is_idempotent_and_enforces_hard_limit(self) -> None:
        first = record_usage(
            context=self.context,
            quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=1,
            idempotency_key="slot-1",
            source="test",
        )
        replay = record_usage(
            context=self.context,
            quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=1,
            idempotency_key="slot-1",
            source="test",
        )
        self.assertEqual(first.entry.id, replay.entry.id)
        self.assertEqual(replay.used_value, 1)
        record_usage(
            context=self.context,
            quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=1,
            idempotency_key="slot-2",
            source="test",
        )
        with self.assertRaises(QuotaExceeded):
            record_usage(
                context=self.context,
                quota_key=QuotaKey.AI_AGENT_SLOTS,
                quantity=1,
                idempotency_key="slot-3",
                source="test",
            )

    def test_correction_is_compensating_and_counter_rebuilds(self) -> None:
        original = record_usage(
            context=self.context,
            quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=1,
            idempotency_key="original",
            source="test",
        ).entry
        correction = record_adjustment(
            context=self.context,
            quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=-1,
            idempotency_key="correction",
            reason="Duplicate upstream event",
            correction_of=original,
        ).entry
        self.assertEqual(correction.correction_of, original)
        self.assertEqual(UsageLedgerEntry.objects.count(), 2)
        counter = UsageCounter.objects.get()
        counter.used_value = 99
        counter.save(update_fields=["used_value"])
        self.assertEqual(
            rebuild_counter(context=self.context, quota_key=QuotaKey.AI_AGENT_SLOTS).used_value,
            0,
        )

        with self.assertRaises(ValidationError):
            original.delete()
        with self.assertRaises(DatabaseError), transaction.atomic():
            UsageLedgerEntry.objects.filter(pk=original.pk).update(quantity=2)
