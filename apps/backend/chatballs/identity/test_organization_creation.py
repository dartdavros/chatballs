"""Создание организации из интерфейса: кнопка «Добавить организацию» (A1)."""

from __future__ import annotations

import json

from django.test import TestCase, override_settings

from chatballs.ai.models import KnowledgeCategory
from chatballs.identity.models import (
    AuditEvent,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient

URL = "/api/v1/organizations/"


@override_settings(ROOT_URLCONF="chatballs_backend.urls_app")
class OrganizationCreationTests(TestCase):
    def setUp(self) -> None:
        self.first = Organization.objects.create(name="Ателье Норд", slug="atelie-nord")
        self.owner = HumanUser.objects.create_user(
            email="owner@example.test", password="Owner-pass-123!", full_name="Елена"
        )
        OrganizationMembership.objects.create(
            organization=self.first,
            user=self.owner,
            role=EmployeeRole.OWNER,
            position_title="Владелец",
        )
        self.employee = HumanUser.objects.create_user(
            email="employee@example.test", password="Emp-pass-1234!", full_name="Иван"
        )
        OrganizationMembership.objects.create(
            organization=self.first,
            user=self.employee,
            role=EmployeeRole.EMPLOYEE,
            position_title="Оператор",
        )

    def _post(self, user: HumanUser, **body):
        client = TenantAPIClient()
        client.force_login(user)
        return client.post(
            URL,
            data=json.dumps({"name": "Вторая компания", "timezone": "Europe/Moscow", **body}),
            content_type="application/json",
        )

    def test_owner_creates_organization_and_becomes_its_owner(self) -> None:
        response = self._post(self.owner, language="en")

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        created = Organization.objects.get(public_id=payload["organizationPublicId"])
        self.assertEqual(created.name, "Вторая компания")
        self.assertEqual(created.language, "en")
        self.assertEqual(created.status, "ACTIVE")
        membership = OrganizationMembership.objects.get(organization=created, user=self.owner)
        self.assertEqual(membership.role, EmployeeRole.OWNER)
        self.assertTrue(KnowledgeCategory.objects.filter(organization=created).exists())
        # Список членств в ответе уже содержит новую организацию: интерфейсу
        # есть куда переключиться без повторного запроса сессии.
        self.assertEqual(
            {item["organizationPublicId"] for item in payload["user"]["memberships"]},
            {str(self.first.public_id), str(created.public_id)},
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=created, action="organization.created", actor=self.owner
            ).exists()
        )

    def test_same_name_gets_a_distinct_slug(self) -> None:
        first = self._post(self.owner).json()["organizationPublicId"]
        second = self._post(self.owner).json()["organizationPublicId"]

        slugs = set(Organization.objects.filter(public_id__in=[first, second]).values_list("slug", flat=True))
        self.assertEqual(len(slugs), 2)

    def test_employee_cannot_create_organizations(self) -> None:
        response = self._post(self.employee)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Organization.objects.count(), 1)

    def test_instance_admin_without_memberships_can_create(self) -> None:
        admin = HumanUser.objects.create_user(
            email="admin@example.test", password="Admin-pass-123!", is_instance_admin=True
        )

        response = self._post(admin)

        self.assertEqual(response.status_code, 201, response.content)
        created = Organization.objects.get(public_id=response.json()["organizationPublicId"])
        self.assertTrue(OrganizationMembership.objects.filter(organization=created, user=admin, role=EmployeeRole.OWNER).exists())

    def test_empty_name_is_a_field_error(self) -> None:
        response = self._post(self.owner, name="   ")

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["errors"])
        self.assertEqual(Organization.objects.count(), 1)

    def test_anonymous_is_rejected(self) -> None:
        response = TenantAPIClient().post(URL, data=json.dumps({"name": "X"}), content_type="application/json")

        self.assertIn(response.status_code, {401, 403})

    def test_options_list_timezones_and_languages(self) -> None:
        client = TenantAPIClient()
        client.force_login(self.owner)

        response = client.get(f"{URL}options/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Europe/Moscow", response.json()["timezones"])
        self.assertTrue(response.json()["languages"])
