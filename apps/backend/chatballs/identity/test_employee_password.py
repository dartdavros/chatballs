"""Пароль первичного доступа и сессии сотрудника (дизайн-базлайн v2, E5–E8)."""

import json

from django.test import TestCase

from chatballs.identity.employee_password import generate_initial_password
from chatballs.identity.models import (
    AuditEvent,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient as APIClient


class EmployeePasswordTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Ателье", slug="atelie-pwd")
        self.owner = self._member("owner@atelie.test", EmployeeRole.OWNER)
        self.employee = self._member("operator@atelie.test", EmployeeRole.EMPLOYEE)
        self.client = APIClient()
        self.client.force_authenticate(self.owner.user)

    def _member(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user, organization=self.organization, role=role, position_title="Specialist"
        )

    def _post(self, path: str, body: dict | None = None):
        return self.client.post(path, data=json.dumps(body or {}), content_type="application/json")

    def test_generated_password_is_readable(self) -> None:
        """Пароль вида «kv7-Rt94-Xmz2»: три группы, без похожих символов."""
        password = generate_initial_password()
        groups = password.split("-")
        self.assertEqual([len(part) for part in groups], [3, 4, 4])
        self.assertFalse(set(password) & set("lI0Oo1"))

    def test_reset_show_returns_password_once_and_stores_only_hash(self) -> None:
        response = self._post(
            f"/api/v1/employees/{self.employee.user_id}/reset-password/", {"mode": "show"}
        )
        self.assertEqual(response.status_code, 200)
        password = response.json()["password"]
        self.assertTrue(password)

        self.employee.user.refresh_from_db()
        # В базе только хеш: открытый пароль живёт лишь в этом ответе.
        self.assertNotIn(password, self.employee.user.password)
        self.assertTrue(self.employee.user.check_password(password))
        self.assertTrue(self.employee.user.must_change_password)
        self.assertIsNotNone(self.employee.user.password_changed_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization, action="identity.employee_password_reset"
            ).exists()
        )

    def test_reset_mail_does_not_return_password(self) -> None:
        response = self._post(
            f"/api/v1/employees/{self.employee.user_id}/reset-password/", {"mode": "mail"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["password"])
        self.employee.user.refresh_from_db()
        self.assertFalse(self.employee.user.has_usable_password())

    def test_unknown_password_mode_is_rejected(self) -> None:
        response = self._post(
            f"/api/v1/employees/{self.employee.user_id}/reset-password/", {"mode": "sms"}
        )
        self.assertEqual(response.status_code, 400)

    def test_employee_cannot_reset_another_password(self) -> None:
        client = APIClient()
        client.force_authenticate(self.employee.user)
        response = client.post(
            f"/api/v1/employees/{self.owner.user_id}/reset-password/",
            data=json.dumps({"mode": "show"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_sessions_are_terminated_and_audited(self) -> None:
        response = self._post(f"/api/v1/employees/{self.employee.user_id}/revoke-sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("revoked", response.json())
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization, action="identity.employee_sessions_terminated"
            ).exists()
        )

    def test_create_returns_password_only_in_show_mode(self) -> None:
        shown = self._post(
            "/api/v1/employees/operators/",
            {
                "email": "new@atelie.test",
                "fullName": "Ольга Титова",
                "positionTitle": "Оператор",
                "role": EmployeeRole.EMPLOYEE,
                "passwordMode": "show",
            },
        )
        self.assertEqual(shown.status_code, 201)
        password = shown.json()["password"]
        self.assertTrue(password)
        created = HumanUser.objects.get(email="new@atelie.test")
        self.assertTrue(created.check_password(password))
        self.assertTrue(created.must_change_password)

        mailed = self._post(
            "/api/v1/employees/operators/",
            {
                "email": "mail@atelie.test",
                "fullName": "Павел Зайцев",
                "positionTitle": "Оператор",
                "role": EmployeeRole.EMPLOYEE,
                "passwordMode": "mail",
            },
        )
        self.assertEqual(mailed.status_code, 201)
        self.assertIsNone(mailed.json()["password"])
