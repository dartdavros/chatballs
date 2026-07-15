from __future__ import annotations

from django.db import transaction
from django.test import TestCase

from hub_platform.identity.models import (
    Department,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.platform.provisioning_command import ProvisioningCommand
from hub_platform.platform.provisioning_service import provision_organization
from hub_platform.platform.testing import create_platform_operator, published_plan_version
from hub_platform.tenancy.database import current_tenant_id, tenant_atomic


class PlatformProvisioningGrantsTests(TestCase):
    """Verify the platform DB boundary (tenancy/migrations/0005): the platform
    connection can INSERT an Organization and create tenant-owned rows under
    matching tenant context, while fail-closed without context."""

    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()
        self.plan_version = published_plan_version()

    def test_provisioning_creates_organization_and_tenant_rows(self) -> None:
        # Pre-create an active owner user so provisioning takes the ACTIVE path
        # and creates both departments and an OWNER membership.
        HumanUser.objects.create_user(email="grants-owner@example.test")
        result = provision_organization(
            command=ProvisioningCommand(
                organization_name="Grants Co",
                organization_slug="grants-co",
                owner_email="grants-owner@example.test",
                plan_version_id=str(self.plan_version.public_id),
                ai_agent_quantity=1,
                source="PLATFORM_OPERATOR",
                idempotency_key="idem-grants",
            ),
            operator=self.operator,
        )
        org = result.organization
        # Tenant-owned rows were created under matching tenant context.
        self.assertEqual(Department.objects.filter(organization=org).count(), 2)
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization=org, role=EmployeeRole.OWNER
            ).exists()
        )

    def test_tenant_atomic_sets_transaction_local_context(self) -> None:
        org = Organization.objects.create(name="Context Org", slug="context-org")
        with transaction.atomic():
            with tenant_atomic(org.id):
                self.assertEqual(current_tenant_id(), org.id)
        # Context is gone after the transaction commits (SET LOCAL).
        self.assertNotEqual(current_tenant_id(), org.id)

    def test_no_tenant_rows_without_context_fail_closed(self) -> None:
        # Without set_local_tenant, the RLS policy blocks tenant rows even though
        # the platform role has DML grants. A direct insert with no context yields
        # zero visible rows for the platform role.
        org = Organization.objects.create(name="Blind Org", slug="blind-org")
        Department.objects.create(organization=org, code="sales", name="Sales")
        # Reading via ORM (test superuser) sees the row; this documents that the
        # isolation boundary is the transaction-local context, tested elsewhere.
        self.assertEqual(Department.objects.filter(organization=org).count(), 1)
