"""Адрес установки: смена не должна выбрасывать того, кто её делает.

Владелец меняет адрес заранее — до того, как новый домен начал резолвиться и
получил сертификат, — и сидит при этом на старом. Пока принятым был только
новый адрес, сохранение отвечало «Invalid host» через десять секунд (TTL
кэша), а мастер первого запуска уже закрыт: вернуться было неоткуда.

Здесь же — запрет вешать портал помощи на адрес самой установки: SPA решает,
что рисовать, по ответу ``/api/v1/help/``, и такой портал подменял бы
сотрудникам приложение своим Help Center.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import TestCase

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.instance_settings import (
    InstanceSettings,
    accepted_hosts,
    invalidate_cache,
)
from chatballs.support_portals.models import SupportPortal
from chatballs.testing import TenantAPIClient

PASSWORD = "Owner-Password-2026!"


class InstanceAddressChangeTests(TestCase):
    def setUp(self) -> None:
        self.result = bootstrap_owner(email="address-owner@example.com", password=PASSWORD)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.result.owner)
        row = InstanceSettings.load()
        row.public_host = "203.0.113.10"
        row.public_scheme = "http"
        row.previous_public_host = ""
        row.save(update_fields=["public_host", "public_scheme", "previous_public_host", "updated_at"])
        invalidate_cache()
        self.addCleanup(invalidate_cache)

    def _patch(self, host: str, scheme: str = "https"):
        return self.client.patch(
            "/api/v1/company/administration/instance/",
            {"publicHost": host, "publicScheme": scheme},
            format="json",
        )

    def test_previous_address_stays_accepted(self) -> None:
        response = self._patch("crm.example.test")

        self.assertEqual(response.status_code, 200, response.content)
        invalidate_cache()
        self.assertEqual(set(accepted_hosts()), {"crm.example.test", "203.0.113.10"})

    def test_old_address_still_answers_after_the_change(self) -> None:
        self._patch("crm.example.test")
        invalidate_cache()

        response = self.client.get("/api/v1/auth/session/", HTTP_HOST="203.0.113.10")

        self.assertEqual(response.status_code, 200, response.content)

    def test_stranger_host_is_still_rejected(self) -> None:
        self._patch("crm.example.test")
        invalidate_cache()

        response = self.client.get("/api/v1/auth/session/", HTTP_HOST="evil.example")

        self.assertEqual(response.status_code, 400)

    def test_only_one_previous_address_is_kept(self) -> None:
        self._patch("first.example.test")
        self._patch("second.example.test")
        invalidate_cache()

        self.assertEqual(set(accepted_hosts()), {"second.example.test", "first.example.test"})

    def test_saving_the_same_address_does_not_shift_history(self) -> None:
        self._patch("crm.example.test")
        self._patch("crm.example.test")
        invalidate_cache()

        self.assertEqual(set(accepted_hosts()), {"crm.example.test", "203.0.113.10"})


class PortalDomainCollisionTests(TestCase):
    def setUp(self) -> None:
        self.result = bootstrap_owner(email="portal-owner@example.com", password=PASSWORD)
        row = InstanceSettings.load()
        row.public_host = "crm.example.test"
        row.previous_public_host = "203.0.113.10"
        row.save(update_fields=["public_host", "previous_public_host", "updated_at"])
        invalidate_cache()
        self.addCleanup(invalidate_cache)

    def _portal(self, custom_domain: str) -> SupportPortal:
        return SupportPortal(
            organization=self.result.organization,
            slug="help",
            name="Help",
            custom_domain=custom_domain,
        )

    def test_installation_address_cannot_become_a_portal_domain(self) -> None:
        with self.assertRaises(ValidationError) as error:
            self._portal("crm.example.test").clean()

        self.assertIn("custom_domain", error.exception.message_dict)

    def test_previous_installation_address_is_also_refused(self) -> None:
        with self.assertRaises(ValidationError):
            self._portal("203.0.113.10").clean()

    def test_unrelated_domain_is_allowed(self) -> None:
        portal = self._portal("help.example.test")

        portal.clean()  # не должно бросать

        self.assertEqual(portal.custom_domain, "help.example.test")
