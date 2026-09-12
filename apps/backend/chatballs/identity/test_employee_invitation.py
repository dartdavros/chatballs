"""Приглашение существующей учётной записи во вторую организацию.

Учётная запись глобальная, членство — по согласию человека: создание
сотрудника с уже занятым e-mail выписывает приглашение, письмо уходит из
воркера с новым токеном, а членство появляется после принятия.
"""

from __future__ import annotations

from django.core import mail
from django.test import TestCase

from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.invitation_models import OrganizationInvitation
from chatballs.identity.invitation_service import MEMBERSHIP_INVITATION_REQUESTED
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient

PASSWORD = "Long-and-strong-passphrase-42"


class InvitationTestBase(TestCase):
    def setUp(self) -> None:
        self.first = Organization.objects.create(name="First", slug="inv-first")
        self.second = Organization.objects.create(name="Second", slug="inv-second")
        self.second_owner = HumanUser.objects.create_user(
            email="second-owner@example.test", password=PASSWORD, full_name="Second Owner"
        )
        self.second_membership = OrganizationMembership.objects.create(
            organization=self.second,
            user=self.second_owner,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )
        self.group = EmployeeGroup.objects.create(organization=self.second, name="Support")
        # Человек уже работает в первой организации.
        self.person = HumanUser.objects.create_user(
            email="person@example.test", password=PASSWORD, full_name="Person"
        )
        OrganizationMembership.objects.create(
            organization=self.first,
            user=self.person,
            role=EmployeeRole.EMPLOYEE,
            position_title="Operator",
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.second_owner)
        self.client.set_tenant(self.second)

    def _create(self, email: str = "person@example.test"):
        return self.client.post(
            "/api/v1/employees/operators/",
            {
                "email": email,
                "fullName": "Person",
                "positionTitle": "Support operator",
                "role": EmployeeRole.EMPLOYEE,
                "passwordMode": "mail",
                "groupIds": [self.group.id],
            },
            format="json",
        )


class InviteExistingUserTests(InvitationTestBase):
    def test_existing_account_gets_an_invitation_instead_of_an_error(self) -> None:
        response = self._create()

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()["invited"])
        self.assertIsNone(response.json()["employee"])
        self.assertFalse(
            OrganizationMembership.objects.filter(user=self.person, organization=self.second).exists()
        )
        invitation = OrganizationInvitation.objects.get(organization=self.second, email="person@example.test")
        self.assertEqual(invitation.role, EmployeeRole.EMPLOYEE)
        self.assertEqual(invitation.position_title, "Support operator")
        self.assertEqual(invitation.group_ids, [self.group.id])
        self.assertTrue(
            OutboxEvent.objects.filter(
                event_type=MEMBERSHIP_INVITATION_REQUESTED, organization=self.second
            ).exists()
        )

    def test_same_organization_still_reports_the_address_as_taken(self) -> None:
        response = self._create(email="second-owner@example.test")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(OrganizationInvitation.objects.filter(organization=self.second).exists())

    def test_worker_sends_the_letter_and_the_link_accepts(self) -> None:
        self._create()
        event = OutboxEvent.objects.get(event_type=MEMBERSHIP_INVITATION_REQUESTED)

        dispatch(event)

        self.assertEqual(len(mail.outbox), 1)
        letter = mail.outbox[0]
        self.assertEqual(letter.to, ["person@example.test"])
        self.assertIn("/join?token=", letter.body)
        token = letter.body.split("/join?token=", 1)[1].split()[0]

        person_client = TenantAPIClient()
        person_client.force_authenticate(self.person)
        accepted = person_client.post("/api/v1/auth/invitations/accept/", {"token": token}, format="json")

        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertEqual(accepted.json()["organizationPublicId"], str(self.second.public_id))
        membership = OrganizationMembership.objects.get(user=self.person, organization=self.second)
        self.assertEqual(membership.role, EmployeeRole.EMPLOYEE)
        self.assertEqual(membership.position_title, "Support operator")
        self.assertEqual([link.group_id for link in membership.group_links.all()], [self.group.id])
        self.assertEqual(
            {item["organizationPublicId"] for item in accepted.json()["user"]["memberships"]},
            {str(self.first.public_id), str(self.second.public_id)},
        )

    def test_reinvite_replaces_the_pending_invitation(self) -> None:
        self._create()
        first = OrganizationInvitation.objects.get(organization=self.second, email="person@example.test")

        self._create()

        first.refresh_from_db()
        self.assertIsNotNone(first.revoked_at)
        self.assertEqual(
            OrganizationInvitation.objects.filter(
                organization=self.second, email="person@example.test", revoked_at__isnull=True
            ).count(),
            1,
        )

    def test_stranger_cannot_use_someone_elses_invitation(self) -> None:
        self._create()
        dispatch(OutboxEvent.objects.get(event_type=MEMBERSHIP_INVITATION_REQUESTED))
        token = mail.outbox[0].body.split("/join?token=", 1)[1].split()[0]
        stranger = HumanUser.objects.create_user(email="stranger@example.test", password=PASSWORD)
        client = TenantAPIClient()
        client.force_authenticate(stranger)

        response = client.post("/api/v1/auth/invitations/accept/", {"token": token}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            OrganizationMembership.objects.filter(user=stranger, organization=self.second).exists()
        )


class PendingInvitationRowsTests(InvitationTestBase):
    """Ожидающие приглашения видны в списке сотрудников и управляются оттуда."""

    def test_list_shows_the_invitation_with_role_position_and_groups(self) -> None:
        self._create()

        payload = self.client.get("/api/v1/employees/").json()

        self.assertEqual(len(payload["invitations"]), 1)
        row = payload["invitations"][0]
        self.assertEqual(row["email"], "person@example.test")
        self.assertEqual(row["fullName"], "Person")
        self.assertEqual(row["role"], EmployeeRole.EMPLOYEE)
        self.assertEqual(row["positionTitle"], "Support operator")
        self.assertEqual([group["id"] for group in row["groups"]], [self.group.id])
        # Фильтры списка действуют и на приглашения.
        self.assertEqual(self.client.get("/api/v1/employees/?role=ADMIN").json()["invitations"], [])
        self.assertEqual(len(self.client.get("/api/v1/employees/?q=person").json()["invitations"]), 1)
        self.assertEqual(self.client.get("/api/v1/employees/?q=nobody").json()["invitations"], [])

    def test_resend_extends_expiry_and_queues_a_new_letter(self) -> None:
        self._create()
        invitation = OrganizationInvitation.objects.get(organization=self.second, email="person@example.test")
        OutboxEvent.objects.filter(event_type=MEMBERSHIP_INVITATION_REQUESTED).delete()

        response = self.client.post(f"/api/v1/employees/invitations/{invitation.id}/resend/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(OutboxEvent.objects.filter(event_type=MEMBERSHIP_INVITATION_REQUESTED).count(), 1)
        refreshed = OrganizationInvitation.objects.get(pk=invitation.id)
        self.assertGreaterEqual(refreshed.expires_at, invitation.expires_at)

    def test_revoke_hides_the_row_and_kills_the_link(self) -> None:
        self._create()
        dispatch(OutboxEvent.objects.get(event_type=MEMBERSHIP_INVITATION_REQUESTED))
        token = mail.outbox[0].body.split("/join?token=", 1)[1].split()[0]
        invitation = OrganizationInvitation.objects.get(organization=self.second, email="person@example.test")

        response = self.client.post(f"/api/v1/employees/invitations/{invitation.id}/revoke/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get("/api/v1/employees/").json()["invitations"], [])
        person_client = TenantAPIClient()
        person_client.force_authenticate(self.person)
        accepted = person_client.post("/api/v1/auth/invitations/accept/", {"token": token}, format="json")
        self.assertEqual(accepted.status_code, 400)

    def test_employee_cannot_manage_invitations(self) -> None:
        self._create()
        invitation = OrganizationInvitation.objects.get(organization=self.second, email="person@example.test")
        operator = HumanUser.objects.create_user(email="operator@example.test", password=PASSWORD)
        OrganizationMembership.objects.create(
            organization=self.second, user=operator, role=EmployeeRole.EMPLOYEE, position_title="Operator"
        )
        client = TenantAPIClient()
        client.force_authenticate(operator)
        client.set_tenant(self.second)

        self.assertEqual(client.post(f"/api/v1/employees/invitations/{invitation.id}/revoke/").status_code, 403)
        self.assertEqual(client.post(f"/api/v1/employees/invitations/{invitation.id}/resend/").status_code, 403)
