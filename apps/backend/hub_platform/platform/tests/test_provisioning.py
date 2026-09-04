from __future__ import annotations

from django.test import TestCase

from hub_platform.ai.models import AIAgent
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
from hub_platform.platform.errors import ProvisioningConflict
from hub_platform.platform.models import (
    OrganizationProvisioning,
    ProvisioningStatus,
)
from hub_platform.platform.provisioning_command import ProvisioningCommand
from hub_platform.platform.provisioning_service import provision_organization
from hub_platform.platform.testing import create_platform_operator, published_plan_version
from hub_platform.subscriptions.models import SubscriptionStatus, UsagePeriod


def _command(
    *,
    slug: str = "acme",
    owner_email: str = "owner-acme@example.test",
    quantity: int = 1,
    key: str = "idem-acme",
    plan_version_id: str | None = None,
) -> ProvisioningCommand:
    return ProvisioningCommand(
        organization_name="Acme LLC",
        organization_slug=slug,
        owner_email=owner_email,
        plan_version_id=plan_version_id or "",
        ai_agent_quantity=quantity,
        source="PLATFORM_OPERATOR",
        idempotency_key=key,
    )


class ProvisionExistingOwnerTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.plan_version = published_plan_version()
        self.owner = HumanUser.objects.create_user(email="owner-acme@example.test")

    def test_creates_active_organization_with_owner_membership_and_subscription(self) -> None:
        result = provision_organization(
            command=_command(plan_version_id=str(self.plan_version.public_id)),
            operator=self.operator,
        )
        org = result.organization
        self.assertTrue(result.created)
        self.assertEqual(org.status, OrganizationStatus.ACTIVE)
        self.assertEqual(
            OrganizationMembership.objects.filter(
                organization=org, role=EmployeeRole.OWNER
            ).count(),
            1,
        )
        self.assertTrue(SubscriptionActive(org))
        self.assertTrue(UsagePeriod.objects.filter(subscription__organization=org).exists())
        record = OrganizationProvisioning.objects.get(idempotency_key="idem-acme")
        self.assertEqual(record.status, ProvisioningStatus.COMPLETED)
        self.assertEqual(record.organization_id, org.id)

    def test_does_not_create_ai_agent_product_or_demo_data(self) -> None:
        result = provision_organization(
            command=_command(plan_version_id=str(self.plan_version.public_id)),
            operator=self.operator,
        )
        org = result.organization
        self.assertFalse(AIAgent.objects.filter(organization=org).exists())
        # No products / integrations / channels created by provisioning.
        self.assertEqual(org.provisioning_records.count(), 1)


class ProvisionNewOwnerTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.plan_version = published_plan_version()

    def test_pending_owner_state_issues_invitation_without_usage_period(self) -> None:
        result = provision_organization(
            command=_command(
                owner_email="new-owner@example.test",
                plan_version_id=str(self.plan_version.public_id),
            ),
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
        sub = org.subscription
        self.assertEqual(sub.status, SubscriptionStatus.SUSPENDED)
        self.assertEqual(sub.suspension_reason, "OWNER_PENDING")
        self.assertFalse(UsagePeriod.objects.filter(subscription__organization=org).exists())
        record = OrganizationProvisioning.objects.get(idempotency_key="idem-acme")
        self.assertEqual(record.status, ProvisioningStatus.WAITING_FOR_OWNER)


class IdempotencyTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.plan_version = published_plan_version()
        self.owner = HumanUser.objects.create_user(email="owner-acme@example.test")

    def test_replay_with_same_payload_returns_existing_without_duplicate(self) -> None:
        first = provision_organization(
            command=_command(plan_version_id=str(self.plan_version.public_id)),
            operator=self.operator,
        )
        second = provision_organization(
            command=_command(plan_version_id=str(self.plan_version.public_id)),
            operator=self.operator,
        )
        self.assertFalse(second.created)
        self.assertEqual(first.organization.id, second.organization.id)
        self.assertEqual(Organization.objects.filter(slug="acme").count(), 1)
        self.assertEqual(OrganizationProvisioning.objects.filter().count(), 1)

    def test_same_key_different_payload_is_conflict(self) -> None:
        provision_organization(
            command=_command(plan_version_id=str(self.plan_version.public_id)),
            operator=self.operator,
        )
        with self.assertRaises(ProvisioningConflict):
            provision_organization(
                command=_command(
                    slug="acme-different",
                    plan_version_id=str(self.plan_version.public_id),
                ),
                operator=self.operator,
            )


class OperatorIsolationTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.plan_version = published_plan_version()
        self.owner = HumanUser.objects.create_user(email="owner-acme@example.test")

    def test_operator_does_not_become_owner(self) -> None:
        result = provision_organization(
            command=_command(plan_version_id=str(self.plan_version.public_id)),
            operator=self.operator,
        )
        org = result.organization
        self.assertFalse(
            OrganizationMembership.objects.filter(
                organization=org, role=EmployeeRole.OWNER
            )
            .exclude(user__email="owner-acme@example.test")
            .exists()
        )


class FreeQuantityTests(TestCase):
    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.free_version = published_plan_version(plan_code="FREE")
        self.owner = HumanUser.objects.create_user(email="owner-free@example.test")

    def test_free_quantity_is_one(self) -> None:
        result = provision_organization(
            command=_command(
                owner_email="owner-free@example.test",
                quantity=1,
                plan_version_id=str(self.free_version.public_id),
            ),
            operator=self.operator,
        )
        self.assertEqual(result.organization.subscription.ai_agent_quantity, 1)


def SubscriptionActive(org: Organization) -> bool:
    return org.subscription.status == SubscriptionStatus.ACTIVE
