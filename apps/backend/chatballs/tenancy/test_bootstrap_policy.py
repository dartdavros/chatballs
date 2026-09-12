from __future__ import annotations

from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase

from chatballs.identity.models import EmployeeRole, Organization, OrganizationMembership
from chatballs.identity.setup import SetupInput, complete_setup
from chatballs.tenancy.ingress import organization_ids
from chatballs.tenancy.lookup import instance_has_organizations


class AppRoleBootstrapPolicyTests(TransactionTestCase):
    """Мастер первого запуска работает ролью app (tenancy/0032).

    Пока организаций нет, роль app вправе создать первую; сразу после этого
    INSERT для неё закрыт, и следующие организации создаёт только роль
    platform. Проверяется под реальной runtime-ролью, а не владельцем кластера.
    """

    def _set_role(self, role: str) -> None:
        with connection.cursor() as cursor:
            cursor.execute(f"SET ROLE {role}")

    def _reset_role(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")

    def test_setup_creates_first_organization_under_app_role_only_once(self) -> None:
        self._set_role("chatballs_runtime_app")
        try:
            result = complete_setup(
                SetupInput(
                    organization_name="Bootstrap Co",
                    full_name="First Owner",
                    email="first-owner@example.test",
                    password="Long-and-strong-passphrase-42",
                )
            )
            # Без контекста строки организаций роли app не видны (tenancy/0033):
            # факт создания проверяется через каталог.
            self.assertTrue(instance_has_organizations())
            self.assertEqual(len(organization_ids()), 1)
            with transaction.atomic(), self.assertRaises(DatabaseError):
                Organization.objects.create(name="Second", slug="second-co")
        finally:
            self._reset_role()
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization=result.organization,
                user=result.owner,
                role=EmployeeRole.OWNER,
            ).exists()
        )
