from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from hub_platform.identity.invitation_service import (
    InvitationError,
    accept_invitation,
    issue_invitation,
)
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
def _pending_org(slug: str = "pending-org") -> Organization:
    return Organization.objects.create(
        name="Pending Org",
        slug=slug,
        status=OrganizationStatus.PENDING_OWNER,
    )


class AcceptInvitationTests(TestCase):
    def setUp(self) -> None:
        self.org = _pending_org()
        self.user = HumanUser.objects.create_user(email="new-owner@example.test")
        issued = issue_invitation(
            organization=self.org,
            email="new-owner@example.test",
            role=EmployeeRole.OWNER,
            expires_at=timezone.now() + timedelta(days=7),
            created_by=None,
        )
        self.token = issued.token

    def test_accept_creates_owner_membership_and_activates_org(self) -> None:
        result = accept_invitation(token=self.token, user=self.user)
        self.assertEqual(result.membership.role, EmployeeRole.OWNER)
        self.org.refresh_from_db()
        self.assertEqual(self.org.status, OrganizationStatus.ACTIVE)

    def test_re_accept_same_token_is_idempotent(self) -> None:
        accept_invitation(token=self.token, user=self.user)
        # Second accept of the same token should not create a second membership.
        accept_invitation(token=self.token, user=self.user)
        self.assertEqual(
            OrganizationMembership.objects.filter(
                organization=self.org, role=EmployeeRole.OWNER
            ).count(),
            1,
        )

    def test_accept_with_mismatched_email_is_rejected(self) -> None:
        other = HumanUser.objects.create_user(email="someone-else@example.test")
        with self.assertRaises(InvitationError):
            accept_invitation(token=self.token, user=other)

    def test_accept_expired_invitation_is_rejected(self) -> None:
        # The invitation model forbids creating rows already expired, so move an
        # existing one into the past directly to exercise the expiry guard.
        self.org.invitations.update(expires_at=timezone.now() - timedelta(days=1))
        with self.assertRaises(InvitationError):
            accept_invitation(token=self.token, user=self.user)
