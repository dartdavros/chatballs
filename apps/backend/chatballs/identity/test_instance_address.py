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

import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from chatballs.identity import instance_settings
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.instance_settings import (
    InstanceSettings,
    accepted_hosts,
    invalidate_cache,
)
from chatballs.identity.models import EmployeeRole, HumanUser, Organization, OrganizationMembership
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
            "/api/v1/instance/settings/",
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


class InstanceSettingsAccessTests(TestCase):
    """Настройки установки меняет только её администратор.

    Владелец другой организации видит адреса TURN (карточка relay), но не может
    переключить общий SMTP или адрес установки; сотрудник не видит ничего.
    """

    def setUp(self) -> None:
        self.result = bootstrap_owner(email="instance-owner@example.com", password=PASSWORD)
        self.other_org = Organization.objects.create(name="Other", slug="other-org")
        self.other_owner = HumanUser.objects.create_user(
            email="other-owner@example.com", password=PASSWORD, full_name="Other Owner"
        )
        OrganizationMembership.objects.create(
            organization=self.other_org,
            user=self.other_owner,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )
        self.employee = HumanUser.objects.create_user(
            email="employee@example.com", password=PASSWORD, full_name="Employee"
        )
        OrganizationMembership.objects.create(
            organization=self.other_org,
            user=self.employee,
            role=EmployeeRole.EMPLOYEE,
            position_title="Operator",
        )

    def _client(self, user: HumanUser) -> TenantAPIClient:
        client = TenantAPIClient()
        client.force_authenticate(user)
        return client

    def test_setup_owner_is_instance_admin_and_may_change_settings(self) -> None:
        self.assertTrue(self.result.owner.is_instance_admin)
        response = self._client(self.result.owner).patch(
            "/api/v1/instance/settings/",
            {"publicHost": "crm.example.test", "publicScheme": "https"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_organization_owner_reads_but_cannot_change(self) -> None:
        client = self._client(self.other_owner)
        self.assertEqual(client.get("/api/v1/instance/settings/").status_code, 200)
        self.assertEqual(client.get("/api/v1/instance/storage/").status_code, 200)
        denied = client.patch(
            "/api/v1/instance/settings/",
            {"publicHost": "crm.example.test", "publicScheme": "https"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(
            client.post("/api/v1/instance/settings/email-check/", {}, format="json").status_code, 403
        )
        self.assertEqual(
            client.patch("/api/v1/instance/storage/", {"backend": "LOCAL"}, format="json").status_code,
            403,
        )

    def test_employee_sees_nothing(self) -> None:
        client = self._client(self.employee)
        self.assertEqual(client.get("/api/v1/instance/settings/").status_code, 403)
        self.assertEqual(client.get("/api/v1/instance/storage/").status_code, 403)

    def test_session_reports_the_flag(self) -> None:
        admin_session = self._client(self.result.owner).get("/api/v1/auth/session/").json()
        owner_session = self._client(self.other_owner).get("/api/v1/auth/session/").json()
        self.assertTrue(admin_session["user"]["isInstanceAdmin"])
        self.assertFalse(owner_session["user"]["isInstanceAdmin"])

    def test_old_organization_scoped_paths_are_gone(self) -> None:
        client = self._client(self.result.owner)
        client.organization_public_id = str(self.result.organization.public_id)
        response = client.get(
            f"/api/v1/organizations/{self.result.organization.public_id}/company/administration/instance/"
        )
        self.assertEqual(response.status_code, 404)


class StaleHostCacheTests(TestCase):
    """Адрес, записанный мастером в одном процессе, принимает и соседний.

    Кэш адреса живёт в каждом процессе gunicorn по 10 секунд. Соседний процесс
    с устаревшим кэшем отвечал «Invalid host» на первый же запрос после
    мастера — в интерфейсе это «Ошибка загрузки», исчезавшая после обновления
    страницы. Промах по хосту теперь перечитывает кэш.
    """

    def setUp(self) -> None:
        self.result = bootstrap_owner(email="cache-owner@example.com", password=PASSWORD)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.result.owner)
        # Строка настроек должна существовать: update() ниже её не создаёт.
        InstanceSettings.load()
        self.addCleanup(invalidate_cache)

    def _stale_cache_with_no_host(self) -> None:
        # Соседний процесс: только что прочитал пустой адрес, TTL ещё не вышел.
        instance_settings._cached = (time.monotonic(), ("", ""))
        instance_settings._last_miss_refresh = 0.0

    def test_host_written_by_another_process_is_accepted_at_once(self) -> None:
        self._stale_cache_with_no_host()
        # Запись мимо save(): invalidate_cache() в этом процессе не вызывается,
        # как и в реальности, где мастер отработал в другом воркере.
        InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).update(
            public_host="crm.example.test"
        )

        response = self.client.get("/api/v1/auth/session/", HTTP_HOST="crm.example.test")

        self.assertEqual(response.status_code, 200, response.content)

    def test_unknown_host_does_not_reread_more_than_once_a_second(self) -> None:
        InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).update(
            public_host="crm.example.test"
        )
        self._stale_cache_with_no_host()
        self.assertEqual(self.client.get("/api/v1/auth/session/", HTTP_HOST="evil.example").status_code, 400)
        # Первый промах перечитал кэш и уже знает настоящий адрес.
        self.assertEqual(set(accepted_hosts()), {"crm.example.test"})
        # Второй промах в ту же секунду базу не трогает: кэш подменён, но не перечитан.
        instance_settings._cached = (time.monotonic(), ("", ""))
        self.assertEqual(self.client.get("/api/v1/auth/session/", HTTP_HOST="evil.example").status_code, 400)
        self.assertEqual(accepted_hosts(), ())
