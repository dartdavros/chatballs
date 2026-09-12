"""Приглашение владельца из платформенного провижининга доходит до человека.

Учётной записи может ещё не быть: письмо уходит из воркера, а по ссылке
человек задаёт имя и пароль, принимает приглашение и оказывается владельцем
активированной организации. Существующая учётная запись идёт на обычный вход.
"""

from __future__ import annotations

from django.core import mail
from django.test import TestCase, override_settings

from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.invitation_service import OWNER_INVITATION_REQUESTED
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.platform.provisioning_command import ProvisioningCommand
from chatballs.platform.provisioning_service import provision_organization
from chatballs.platform.testing import create_platform_operator
from chatballs.testing import TenantAPIClient

PASSWORD = "Very-strong-passphrase-42"


@override_settings(ROOT_URLCONF="chatballs_backend.urls_app")
class OwnerInvitationFlowTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()

    def _provision(self, email: str = "new-owner@example.test"):
        return provision_organization(
            command=ProvisioningCommand(
                organization_name="Fresh Co",
                organization_slug="fresh-co",
                owner_email=email,
                source="PLATFORM_OPERATOR",
                idempotency_key=f"idem-{email}",
            ),
            operator=self.operator,
        )

    def _token_from_mail(self) -> str:
        return mail.outbox[-1].body.split("/join?token=", 1)[1].split()[0]

    def test_letter_goes_out_and_a_new_person_registers_as_owner(self) -> None:
        result = self._provision()
        dispatch(OutboxEvent.objects.get(event_type=OWNER_INVITATION_REQUESTED))

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new-owner@example.test"])
        token = self._token_from_mail()
        client = TenantAPIClient()

        preview = client.get(f"/api/v1/auth/invitations/preview/?token={token}").json()
        self.assertEqual(preview["valid"], True)
        self.assertEqual(preview["organizationName"], "Fresh Co")
        self.assertFalse(preview["accountExists"])

        response = client.post(
            "/api/v1/auth/invitations/register/",
            {"token": token, "fullName": "New Owner", "password": PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["organizationPublicId"], str(result.organization.public_id))
        self.assertEqual(body["user"]["email"], "new-owner@example.test")
        self.assertFalse(body["user"]["isInstanceAdmin"])
        result.organization.refresh_from_db()
        self.assertEqual(result.organization.status, OrganizationStatus.ACTIVE)
        owner = HumanUser.objects.get(email="new-owner@example.test")
        self.assertTrue(owner.check_password(PASSWORD))
        self.assertFalse(owner.must_change_password)
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization=result.organization, user=owner, role=EmployeeRole.OWNER
            ).exists()
        )
        # Сессия установлена: приложение сразу открывается под владельцем.
        self.assertTrue(client.get("/api/v1/auth/session/").json()["authenticated"])

    def test_weak_password_and_empty_name_are_reported_by_field(self) -> None:
        self._provision()
        dispatch(OutboxEvent.objects.get(event_type=OWNER_INVITATION_REQUESTED))
        token = self._token_from_mail()
        client = TenantAPIClient()

        weak = client.post(
            "/api/v1/auth/invitations/register/",
            {"token": token, "fullName": "New Owner", "password": "short"},
            format="json",
        )
        nameless = client.post(
            "/api/v1/auth/invitations/register/",
            {"token": token, "fullName": "  ", "password": PASSWORD},
            format="json",
        )

        self.assertEqual(weak.status_code, 400)
        self.assertIn("password", weak.json()["errors"])
        self.assertEqual(nameless.status_code, 400)
        self.assertIn("fullName", nameless.json()["errors"])
        self.assertFalse(HumanUser.objects.filter(email="new-owner@example.test").exists())

    def test_existing_account_is_sent_to_login_and_cannot_register(self) -> None:
        HumanUser.objects.create_user(email="known@example.test", password=PASSWORD, is_active=True)
        # Активная учётная запись получает владение сразу, приглашение не нужно:
        # проверяем ветку через приглашение сотрудника той же организации.
        result = self._provision(email="known-owner@example.test")
        dispatch(OutboxEvent.objects.get(event_type=OWNER_INVITATION_REQUESTED))
        token = self._token_from_mail()
        HumanUser.objects.create_user(email="known-owner@example.test", password=PASSWORD)
        client = TenantAPIClient()

        preview = client.get(f"/api/v1/auth/invitations/preview/?token={token}").json()
        register = client.post(
            "/api/v1/auth/invitations/register/",
            {"token": token, "fullName": "Someone", "password": PASSWORD},
            format="json",
        )

        self.assertTrue(preview["accountExists"])
        self.assertEqual(register.status_code, 400)
        self.assertEqual(register.json()["code"], "account_exists")
        self.assertEqual(result.organization.status, OrganizationStatus.PENDING_OWNER)

    def test_unknown_token_previews_as_invalid(self) -> None:
        response = TenantAPIClient().get("/api/v1/auth/invitations/preview/?token=nope")
        self.assertEqual(response.json(), {"valid": False})
