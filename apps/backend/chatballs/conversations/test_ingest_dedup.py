"""Повторная доставка входящего не должна ломать транзакцию.

Дедупликация ставит запись в inbox и ловит IntegrityError на повторе. Ловить
его без точки сохранения нельзя: Postgres обрывает транзакцию целиком, и
следующий же запрос падает с TransactionManagementError. А вызывают это
изнутри транзакции — воркер держит ``tenant_atomic`` на весь цикл поллинга,
так что первый повтор ронял не дедупликацию, а весь цикл организации.
"""

from __future__ import annotations

from django.db import transaction
from django.test import TestCase

from chatballs.conversations.ingest import _already_processed
from chatballs.events.models import InboxEvent
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import system_tenant_context


class InboundDeduplicationTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_owner(email="ingest-owner@example.com", password="Owner-Password-2026!")
        self.context = system_tenant_context(result.organization)

    def test_repeat_is_reported_without_breaking_the_transaction(self) -> None:
        with tenant_atomic(self.context):
            first = _already_processed(self.context, "telegram:1", "update-42", "привет")
            second = _already_processed(self.context, "telegram:1", "update-42", "привет")

            self.assertFalse(first)
            self.assertTrue(second)

            # Главное: транзакция жива и дальше в ней можно работать. Раньше
            # именно здесь всё и разваливалось.
            self.assertEqual(
                InboxEvent.objects.filter(external_event_id="update-42").count(), 1
            )

    def test_repeat_does_not_roll_back_work_done_earlier(self) -> None:
        with transaction.atomic():
            with tenant_atomic(self.context):
                _already_processed(self.context, "max:7", "update-1", "первое")
                _already_processed(self.context, "max:7", "update-1", "первое")
                _already_processed(self.context, "max:7", "update-2", "второе")

        self.assertEqual(InboxEvent.objects.filter(source="max:7").count(), 2)

    def test_different_sources_do_not_collide(self) -> None:
        with tenant_atomic(self.context):
            self.assertFalse(_already_processed(self.context, "telegram:1", "shared-id", "текст"))
            self.assertFalse(_already_processed(self.context, "max:2", "shared-id", "текст"))
