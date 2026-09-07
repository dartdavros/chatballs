import json

from django.test import TestCase

from chatballs.ai.models import KnowledgeCategory
from chatballs.identity.instance_settings import (
    InstanceSettings,
    invalidate_cache,
    public_base_url,
)
from chatballs.identity.models import (
    AuditEvent,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient as APIClient

VALID = {
    "organizationName": "Ателье Норд",
    "fullName": "Елена  Кузнецова",
    "email": "E.Kuznetsova@atelie-nord.ru",
    "password": "Nord-Atelier-2026!",
}


class SetupWizardTests(TestCase):
    """Мастер первого запуска: одна форма в браузере, никаких параметров в .env."""

    def setUp(self) -> None:
        self.client = APIClient()

    def complete(self, **overrides):
        extra = {key: overrides.pop(key) for key in list(overrides) if key.startswith("HTTP_")}
        body = {**VALID, **overrides}
        return self.client.post(
            "/api/v1/setup/complete/",
            data=json.dumps(body),
            content_type="application/json",
            **extra,
        )

    def test_setup_remembers_the_address_it_was_opened_on(self) -> None:
        """Коробку открывают по IP сервера: этот адрес и есть её публичный.

        Другого источника адреса у установки нет — в .env его никто не задаёт,
        а без него сразу после мастера все запросы упёрлись бы в проверку хоста.
        """
        invalidate_cache()

        response = self.complete(HTTP_HOST="203.0.113.10")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(InstanceSettings.load().public_host, "203.0.113.10")

    def test_remembered_address_keeps_working_after_setup(self) -> None:
        self.complete(HTTP_HOST="crm.example.test")
        invalidate_cache()

        response = self.client.get("/api/v1/setup/", HTTP_HOST="crm.example.test")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["needsSetup"])

    def test_external_links_use_the_address_from_the_wizard(self) -> None:
        """Ссылки на файлы уходят клиенту в мессенджер: «localhost» там мёртв.

        Адрес берётся из мастера, а не из переменной окружения, которой на
        свежей установке никто не задаёт.
        """
        invalidate_cache()

        self.complete(HTTP_HOST="crm.example.test")
        invalidate_cache()

        self.assertEqual(public_base_url(), "http://crm.example.test")

    def test_fresh_instance_needs_setup(self) -> None:
        response = self.client.get("/api/v1/setup/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["needsSetup"])

    def test_complete_creates_organization_owner_and_logs_in(self) -> None:
        response = self.complete()

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        user = payload["user"]
        self.assertEqual(user["email"], "e.kuznetsova@atelie-nord.ru")
        self.assertEqual(user["fullName"], "Елена Кузнецова")
        self.assertFalse(user["mustChangePassword"])
        self.assertEqual(len(user["memberships"]), 1)
        self.assertEqual(user["memberships"][0]["role"], EmployeeRole.OWNER)
        self.assertEqual(user["memberships"][0]["organizationName"], "Ателье Норд")

        organization = Organization.objects.get()
        # Кириллическое имя не даёт slug — берётся нейтральный.
        self.assertEqual(organization.slug, "organization")
        owner = HumanUser.objects.get(email="e.kuznetsova@atelie-nord.ru")
        self.assertTrue(owner.check_password(VALID["password"]))
        self.assertTrue(owner.is_superuser)
        membership = OrganizationMembership.objects.get(user=owner, organization=organization)
        self.assertEqual(membership.role, EmployeeRole.OWNER)
        self.assertTrue(KnowledgeCategory.objects.filter(organization=organization).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=organization, action="identity.instance_setup_completed"
            ).exists()
        )

        # Сессия установлена: приложение сразу открывается под владельцем.
        session = self.client.get("/api/v1/auth/session/")
        self.assertTrue(session.json()["authenticated"])

    def test_latin_name_becomes_slug(self) -> None:
        self.complete(organizationName="Nord Atelier & Co")
        self.assertEqual(Organization.objects.get().slug, "nord-atelier-co")

    def test_setup_closes_after_first_owner(self) -> None:
        self.assertEqual(self.complete().status_code, 201)

        self.assertFalse(self.client.get("/api/v1/setup/").json()["needsSetup"])
        second = APIClient().post(
            "/api/v1/setup/complete/",
            data=json.dumps({**VALID, "email": "other@atelie-nord.ru"}),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(HumanUser.objects.count(), 1)

    def test_validation_errors_name_the_fields(self) -> None:
        response = self.complete(organizationName="  ", fullName="", email="not-an-email")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            set(response.json()["errors"]), {"organizationName", "fullName", "email"}
        )
        self.assertFalse(Organization.objects.exists())

    def test_weak_password_is_rejected_before_anything_is_written(self) -> None:
        response = self.complete(password="password")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])
        self.assertFalse(Organization.objects.exists())
        self.assertFalse(HumanUser.objects.exists())
