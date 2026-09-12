"""Сбой опроса подключения: пауза с удвоением и тишина в журнале.

Раньше подключение с ненастоящим токеном писало предупреждение каждые три
секунды. Теперь после сбоя оно пропускается с растущей паузой, журнал видит
первый сбой, выход на максимальную паузу и восстановление, а курсор при
сбое не двигается. Демо-подключения не опрашиваются вовсе.
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.conversations import poller
from chatballs.conversations.transports import backoff, poll
from chatballs.conversations.transports.errors import PollFailed
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration, IntegrationKind, IntegrationProvider
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class PollBackoffTests(TestCase):
    def setUp(self) -> None:
        backoff.reset()
        self.addCleanup(backoff.reset)
        self.organization = Organization.objects.create(name="Poll", slug="poll-org")
        with tenant_atomic(self.organization.id):
            self.channel = Channel.objects.create(organization=self.organization, name="Main", code="main")
            self.integration = Integration.objects.create(
                organization=self.organization,
                kind=IntegrationKind.MESSENGER,
                provider=IntegrationProvider.TELEGRAM,
                name="Bot",
                secret="0000:not-a-token",
                channel=self.channel,
                poll_marker="41",
            )

    def _fail(self, *_args, **_kwargs):
        raise PollFailed("HTTP Error 401: Unauthorized")

    def test_failure_is_logged_once_and_then_skipped(self) -> None:
        with mock.patch.dict(poller.transports._POLL, {IntegrationProvider.TELEGRAM: self._fail}):
            with self.assertLogs("chatballs.conversations.transports.backoff", level="WARNING") as logs:
                self.assertEqual(poll(self.integration), ([], "41"))
            self.assertEqual(len(logs.output), 1)
            self.assertIn("401", logs.output[0])
            # Пока пауза не вышла, транспорт не вызывается и журнал молчит.
            with mock.patch.object(backoff, "_now", return_value=backoff._now()):
                with self.assertNoLogs("chatballs.conversations.transports.backoff", level="WARNING"):
                    self.assertEqual(poll(self.integration), ([], "41"))
            self.assertTrue(backoff.should_skip(self.integration.id))

    def test_delay_doubles_up_to_the_cap_and_recovery_is_logged(self) -> None:
        clock = [1000.0]
        with mock.patch.object(backoff, "_now", side_effect=lambda: clock[0]):
            with mock.patch.dict(poller.transports._POLL, {IntegrationProvider.TELEGRAM: self._fail}):
                delays = []
                for _ in range(10):
                    poll(self.integration)
                    state = backoff._failures[self.integration.id]
                    delays.append(state.delay)
                    clock[0] = state.next_attempt_at  # ждём ровно до следующей попытки
            self.assertEqual(delays[:3], [6.0, 12.0, 24.0])
            self.assertEqual(delays[-1], backoff.MAX_DELAY_SECONDS)
            self.assertTrue(all(delay <= backoff.MAX_DELAY_SECONDS for delay in delays))

            with mock.patch.dict(poller.transports._POLL, {IntegrationProvider.TELEGRAM: lambda _i: ([], "42")}):
                with self.assertLogs("chatballs.conversations.transports.backoff", level="INFO") as logs:
                    self.assertEqual(poll(self.integration), ([], "42"))
            self.assertIn("recovered", logs.output[0])
            self.assertNotIn(self.integration.id, backoff._failures)

    def test_demo_seed_connections_are_not_polled(self) -> None:
        with tenant_atomic(self.organization.id):
            Integration.objects.filter(pk=self.integration.pk).update(config={"demoSeed": True})
            context = TenantContext.for_resource(self.organization)
            with mock.patch("chatballs.conversations.poller.transports.poll") as polled:
                poller.poll_all_messengers(context)
        polled.assert_not_called()
