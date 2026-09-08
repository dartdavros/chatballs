from __future__ import annotations

from django.test import TestCase

from chatballs.identity.models import Organization
from chatballs.tenancy.models import OrganizationStorageUsage, StorageReservation
from chatballs.tenancy.storage_quota import (
    finalize_storage,
    release_storage,
    reserve_storage,
)
from chatballs.testing import system_tenant_context


class StorageReserveFinalizeReleaseTests(TestCase):
    """SPEC-HUB-0022 §10: reserve/finalize/release — идемпотентный технический
    учёт занятого места. Лимитов больше нет (ADR-CHATBALLS-0042 §2): сервис никогда
    не отказывает по квоте."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Stor", slug="stor")
        self.context = system_tenant_context(self.organization)

    def _usage(self) -> OrganizationStorageUsage:
        # refresh_from_db: the service mutates rows via F-expressions, so the cached
        # Python value can hold a CombinedExpression instead of the persisted int.
        self.organization.storage_usage.refresh_from_db()
        return self.organization.storage_usage

    def test_reserve_accumulates_reserved_bytes_without_limits(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=700, idempotency_key="up:1"
        )
        # Тарифной ёмкости нет: второе резервирование любого размера проходит.
        reserve_storage(
            context=self.context, expected_bytes=400, idempotency_key="up:2"
        )
        self.assertEqual(self._usage().reserved_bytes, 1100)
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

    def test_finalize_overrun_consumes_actual_size(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=500, idempotency_key="up:1"
        )
        # Фактический размер превысил оценку — учитывается реальный размер.
        finalize_storage(
            context=self.context, idempotency_key="up:1", actual_bytes=900
        )
        self.assertEqual(self._usage().reserved_bytes, 0)
        self.assertEqual(self._usage().bytes_used, 900)

    def test_release_returns_reserved_bytes_on_failure(self) -> None:
        reserve_storage(
            context=self.context, expected_bytes=600, idempotency_key="up:1"
        )
        release_storage(context=self.context, idempotency_key="up:1")
        self.assertEqual(self._usage().reserved_bytes, 0)
        self.assertEqual(self._usage().bytes_used, 0)

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
