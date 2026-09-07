"""SPEC-HUB-0027 §12 — приведение данных перед включением инвариантов P1-P2.

Схема между `channels.0004` и `channels.0005` не меняется: `AlterField` правит
только Python-дефолты. Весь риск миграции сосредоточен в функции приведения
данных, поэтому она проверяется напрямую на реальном реестре моделей — это
честнее, чем поднимать историческое состояние, где `identity` откатывается
рассинхронно со схемой БД.
"""

import importlib

from django.apps import apps
from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.identity.models import Organization

migration = importlib.import_module(
    "chatballs.channels.migrations.0005_enforce_policy_invariants"
)


class PolicyInvariantMigrationTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")

    def _channel(self, code: str, **fields) -> Channel:
        return Channel.objects.create(
            organization=self.organization, code=code, name=code, **fields
        )

    def _run(self) -> None:
        migration.relax_non_product_channels(apps, None)

    def test_clears_commercial_flags(self) -> None:
        # Ровно случай канала acme: checkout и attribution включены.
        violating = self._channel(
            "acme", allow_checkout_actions=True, allow_sales_attribution=True
        )

        self._run()

        violating.refresh_from_db()
        self.assertFalse(violating.allow_checkout_actions)
        self.assertFalse(violating.allow_sales_attribution)
        # Остальные флаги канала не трогаются.
        self.assertTrue(violating.allow_anonymous_sessions)
        self.assertTrue(violating.allow_self_reported_contact)

    def test_is_idempotent(self) -> None:
        self._channel("acme", allow_checkout_actions=True)

        self._run()
        self._run()

        self.assertEqual(
            Channel.objects.filter(allow_checkout_actions=True).count(),
            0,
        )
