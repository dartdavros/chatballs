from __future__ import annotations

from django.test import TestCase

from chatballs.ai.models import AIAgent
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.platform.errors import ProvisioningConflict
from chatballs.platform.models import (
    OrganizationProvisioning,
    ProvisioningStatus,
)
from chatballs.platform.provisioning_command import ProvisioningCommand
from chatballs.platform.provisioning_service import provision_organization
from chatballs.platform.testing import create_platform_operator


def _command(
    *,
    slug: str = "acme",
    owner_email: str = "owner-acme@example.test",
    key: str = "idem-acme",
) -> ProvisioningCommand:
    return ProvisioningCommand(
        organization_name="Acme LLC",
        organization_slug=slug,
        owner_email=owner_email,
        source="PLATFORM_OPERATOR",
        idempotency_key=key,
    )


class ProvisionExistingOwnerTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.owner = HumanUser.objects.create_user(email="owner-acme@example.test")

    def test_creates_active_organization_with_owner_membership(self) -> None:
        result = provision_organization(command=_command(), operator=self.operator)
        org = result.organization
        self.assertTrue(result.created)
        self.assertEqual(org.status, OrganizationStatus.ACTIVE)
        self.assertEqual(
            OrganizationMembership.objects.filter(
                organization=org, role=EmployeeRole.OWNER
            ).count(),
            1,
        )
        record = OrganizationProvisioning.objects.get(idempotency_key="idem-acme")
        self.assertEqual(record.status, ProvisioningStatus.COMPLETED)
        self.assertEqual(record.organization_id, org.id)

    def test_does_not_create_ai_agent_product_or_demo_data(self) -> None:
        result = provision_organization(command=_command(), operator=self.operator)
        org = result.organization
        self.assertFalse(AIAgent.objects.filter(organization=org).exists())
        # No products / integrations / channels created by provisioning.
        self.assertEqual(org.provisioning_records.count(), 1)


class ProvisionNewOwnerTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()

    def test_pending_owner_state_issues_invitation(self) -> None:
        result = provision_organization(
            command=_command(owner_email="new-owner@example.test"),
            operator=self.operator,
        )
        org = result.organization
        self.assertEqual(org.status, OrganizationStatus.PENDING_OWNER)
        self.assertFalse(
            OrganizationMembership.objects.filter(organization=org).exists()
        )
        self.assertTrue(
            org.invitations.filter(email="new-owner@example.test", role=EmployeeRole.OWNER).exists()
        )
        record = OrganizationProvisioning.objects.get(idempotency_key="idem-acme")
        self.assertEqual(record.status, ProvisioningStatus.WAITING_FOR_OWNER)


class IdempotencyTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.owner = HumanUser.objects.create_user(email="owner-acme@example.test")

    def test_replay_with_same_payload_returns_existing_without_duplicate(self) -> None:
        first = provision_organization(command=_command(), operator=self.operator)
        second = provision_organization(command=_command(), operator=self.operator)
        self.assertFalse(second.created)
        self.assertEqual(first.organization.id, second.organization.id)
        self.assertEqual(Organization.objects.filter(slug="acme").count(), 1)
        self.assertEqual(OrganizationProvisioning.objects.filter().count(), 1)

    def test_same_key_different_payload_is_conflict(self) -> None:
        provision_organization(command=_command(), operator=self.operator)
        with self.assertRaises(ProvisioningConflict):
            provision_organization(
                command=_command(slug="acme-different"),
                operator=self.operator,
            )


class OperatorIsolationTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.owner = HumanUser.objects.create_user(email="owner-acme@example.test")

    def test_operator_does_not_become_owner(self) -> None:
        result = provision_organization(command=_command(), operator=self.operator)
        org = result.organization
        self.assertFalse(
            OrganizationMembership.objects.filter(
                organization=org, role=EmployeeRole.OWNER
            )
            .exclude(user__email="owner-acme@example.test")
            .exists()
        )
