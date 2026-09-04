from datetime import timedelta
from uuid import UUID

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from hub_platform.identity.invitation_service import (
    issue_invitation,
    pending_invitation_for_token,
)
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
)
from hub_platform.identity.policy import ResourceScope, authorize


class MembershipIdentityTests(TestCase):
    def setUp(self) -> None:
        self.first_organization = Organization.objects.create(name="First", slug="first")
        self.second_organization = Organization.objects.create(name="Second", slug="second")
        self.user = HumanUser.objects.create_user(
            email="member@example.test",
            password="Password-123",
        )
        self.first_membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.first_organization,
            role=EmployeeRole.ADMIN,
            position_title="Administrator",
        )

    def test_organization_public_id_is_unique_uuid_and_immutable(self) -> None:
        self.assertIsInstance(self.first_organization.public_id, UUID)
        self.assertNotEqual(
            self.first_organization.public_id,
            self.second_organization.public_id,
        )
        self.first_organization.public_id = self.second_organization.public_id
        with self.assertRaises(ValidationError):
            self.first_organization.save()

    def test_one_user_can_have_different_roles_in_two_organizations(self) -> None:
        second_membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.second_organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Specialist",
        )
        self.assertEqual(self.user.memberships.count(), 2)
        self.assertEqual(self.first_membership.role, EmployeeRole.ADMIN)
        self.assertEqual(second_membership.role, EmployeeRole.EMPLOYEE)

    def test_duplicate_membership_is_rejected(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrganizationMembership.objects.create(
                user=self.user,
                organization=self.first_organization,
                role=EmployeeRole.EMPLOYEE,
                position_title="Duplicate",
            )

    def test_membership_block_does_not_change_global_user_or_other_membership(self) -> None:
        second_membership = OrganizationMembership.objects.create(
            user=self.user,
            organization=self.second_organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Specialist",
        )
        self.first_membership.block()
        self.user.refresh_from_db()
        second_membership.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.first_membership.is_blocked)
        self.assertFalse(second_membership.is_blocked)

    def test_security_credentials_are_global_user_fields(self) -> None:
        self.user.must_change_password = True
        self.user.totp_enabled = True
        self.user.totp_secret = "JBSWY3DPEHPK3PXP"
        self.user.save(update_fields=["must_change_password", "totp_enabled", "totp_secret"])
        for field_name in ("must_change_password", "totp_enabled", "totp_secret"):
            with self.assertRaises(FieldDoesNotExist):
                OrganizationMembership._meta.get_field(field_name)

    def test_membership_keeps_the_historical_table_name(self) -> None:
        self.assertEqual(OrganizationMembership._meta.db_table, "identity_employeeprofile")

    def test_user_has_no_implicit_membership_lookup(self) -> None:
        self.assertFalse(hasattr(self.user, "employee_profile"))
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.second_organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Specialist",
        )
        self.assertFalse(hasattr(self.user, "employee_profile"))

    def test_policy_authorizes_an_explicit_membership(self) -> None:
        self.assertTrue(
            authorize(
                self.first_membership,
                "integrations.manage",
                ResourceScope(self.first_organization.id),
            )
        )
        self.assertFalse(
            authorize(
                self.first_membership,
                "integrations.manage",
                ResourceScope(self.second_organization.id),
            )
        )

    def test_invitation_stores_only_hash_and_can_precede_human_user(self) -> None:
        issued = issue_invitation(
            organization=self.first_organization,
            email="  INVITED@Example.Test ",
            role=EmployeeRole.EMPLOYEE,
            expires_at=timezone.now() + timedelta(hours=24),
            created_by=self.first_membership,
        )
        invitation = OrganizationInvitation.objects.get(pk=issued.invitation.pk)
        self.assertEqual(invitation.email, "invited@example.test")
        self.assertNotEqual(invitation.token_hash, issued.token)
        self.assertNotIn(issued.token, invitation.token_hash)
        self.assertFalse(HumanUser.objects.filter(email=invitation.email).exists())
        self.assertEqual(pending_invitation_for_token(issued.token), invitation)
        self.assertFalse(any(field.name == "password" for field in invitation._meta.fields))

    def test_invitation_creator_cannot_cross_organization(self) -> None:
        with self.assertRaises(ValidationError):
            OrganizationInvitation.objects.create(
                organization=self.second_organization,
                email="invited@example.test",
                role=EmployeeRole.EMPLOYEE,
                token_hash="a" * 64,
                expires_at=timezone.now() + timedelta(hours=24),
                created_by=self.first_membership,
            )
