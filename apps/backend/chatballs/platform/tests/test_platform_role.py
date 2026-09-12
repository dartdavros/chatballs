from __future__ import annotations

from django.db import connection
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    OrganizationInvitation,
    OrganizationMembership,
)
from chatballs.platform.models import OrganizationProvisioning, ProvisioningStatus
from chatballs.platform.testing import create_platform_operator


@override_settings(ROOT_URLCONF="chatballs_backend.urls_platform")
class PlatformRoleProvisioningTests(TransactionTestCase):
    """Провижининг под реальной runtime-ролью platform (tenancy/0031).

    Остальные тесты ходят в базу владельцем кластера и не заметили бы
    отсутствующий GRANT: в деплое backend-platform работает ролью
    chatballs_platform, и без прав на платформенные таблицы уже проверка
    токена падала с «permission denied». Здесь весь HTTP-запрос выполняется
    под этой ролью — от чтения токена до записи приглашения владельца.
    """

    def setUp(self) -> None:
        self.operator, self.token = create_platform_operator()

    def _post(self, token: str, *, slug: str, owner_email: str, key: str):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_platform")
        try:
            return client.post(
                "/api/v1/organizations",
                data={
                    "name": "Role Co",
                    "slug": slug,
                    "owner_email": owner_email,
                    "timezone": "Europe/Moscow",
                    "currency": "RUB",
                },
                format="json",
                HTTP_IDEMPOTENCY_KEY=key,
            )
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")

    def test_unknown_token_is_rejected_not_crashed(self) -> None:
        response = self._post(
            "ctp_not_a_real_token", slug="role-co", owner_email="x@example.test", key="k0"
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_active_owner_is_provisioned_under_platform_role(self) -> None:
        HumanUser.objects.create_user(email="role-owner@example.test")
        response = self._post(
            self.token, slug="role-co", owner_email="role-owner@example.test", key="k1"
        )
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertEqual(payload["owner"]["state"], "active")
        self.assertEqual(payload["provisioning"]["status"], ProvisioningStatus.COMPLETED)
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization__slug="role-co", role=EmployeeRole.OWNER
            ).exists()
        )
        record = OrganizationProvisioning.objects.get(idempotency_key="k1")
        self.assertEqual(record.status, ProvisioningStatus.COMPLETED)

    def test_pending_owner_gets_invitation_under_platform_role(self) -> None:
        response = self._post(
            self.token, slug="role-co", owner_email="new-owner@example.test", key="k2"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["owner"]["state"], "pending_invitation")
        self.assertTrue(
            OrganizationInvitation.objects.filter(
                organization__slug="role-co",
                email="new-owner@example.test",
                role=EmployeeRole.OWNER,
            ).exists()
        )

    def test_replay_is_idempotent_under_platform_role(self) -> None:
        HumanUser.objects.create_user(email="role-owner@example.test")
        first = self._post(
            self.token, slug="role-co", owner_email="role-owner@example.test", key="k3"
        )
        second = self._post(
            self.token, slug="role-co", owner_email="role-owner@example.test", key="k3"
        )
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(OrganizationProvisioning.objects.filter(idempotency_key="k3").count(), 1)
