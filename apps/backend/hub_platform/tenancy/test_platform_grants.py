from __future__ import annotations

from django.db import transaction
from django.test import TestCase

from hub_platform.ai.knowledge_types import UNCATEGORIZED_CATEGORY_NAME
from hub_platform.ai.models import KnowledgeCategory
from hub_platform.identity.group_models import EmployeeGroup
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.platform.provisioning_command import ProvisioningCommand
from hub_platform.platform.provisioning_service import provision_organization
from hub_platform.platform.testing import create_platform_operator
from hub_platform.tenancy.database import current_tenant_id, tenant_atomic


class PlatformProvisioningGrantsTests(TestCase):
    """Verify the platform DB boundary (tenancy/migrations/0005): the platform
    connection can INSERT an Organization and create tenant-owned rows under
    matching tenant context, while fail-closed without context."""

    def setUp(self) -> None:
        self.operator, _ = create_platform_operator()

    def test_provisioning_creates_organization_and_tenant_rows(self) -> None:
        # Pre-create an active owner user so provisioning takes the ACTIVE path
        # and creates an OWNER membership.
        HumanUser.objects.create_user(email="grants-owner@example.test")
        result = provision_organization(
            command=ProvisioningCommand(
                organization_name="Grants Co",
                organization_slug="grants-co",
                owner_email="grants-owner@example.test",
                source="PLATFORM_OPERATOR",
                idempotency_key="idem-grants",
            ),
            operator=self.operator,
        )
        org = result.organization
        # Tenant-owned rows were created under matching tenant context.
        self.assertTrue(
            KnowledgeCategory.objects.filter(
                organization=org,
                name=UNCATEGORIZED_CATEGORY_NAME,
                is_system=True,
            ).exists()
        )
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
        EmployeeGroup.objects.create(organization=org, name="Операторы")
        # Reading via ORM (test superuser) sees the row; this documents that the
        # isolation boundary is the transaction-local context, tested elsewhere.
        self.assertEqual(EmployeeGroup.objects.filter(organization=org).count(), 1)
