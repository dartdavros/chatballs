from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase

from hub_platform.ai.models import AIAgent, Knowledge
from hub_platform.channels.models import Channel
from hub_platform.identity.models import (
    AuditEvent,
    AuditResult,
    Department,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.products.models import Product
from hub_platform.tenancy.database import current_tenant_id, set_local_tenant
from hub_platform.testing import TenantAPIClient


class RowLevelSecurityTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.first = Organization.objects.create(name="First", slug="rls-first")
        self.second = Organization.objects.create(name="Second", slug="rls-second")
        self.first_product = Product.objects.create(
            organization=self.first,
            code="first",
            name="First product",
            ingest_token_hash="first-hash",
        )
        self.second_product = Product.objects.create(
            organization=self.second,
            code="second",
            name="Second product",
            ingest_token_hash="second-hash",
        )
        self.second_department = Department.objects.create(
            organization=self.second,
            code="foreign",
            name="Foreign",
        )
        self.user = HumanUser.objects.create_user(email="rls@example.test")
        OrganizationMembership.objects.create(
            organization=self.first,
            user=self.user,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )

    @staticmethod
    def _set_role(role: str) -> None:
        if role not in {"custocrm_runtime_app", "custocrm_runtime_platform"}:
            raise ValueError("Unexpected test role")
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL ROLE {role}")

    def test_runtime_roles_are_not_owners_or_bypassrls(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolname, rolsuper, rolbypassrls, "
                "pg_has_role(rolname, 'custocrm_schema', 'MEMBER') FROM pg_roles "
                "WHERE rolname IN ('custocrm_runtime_app', 'custocrm_runtime_platform') "
                "ORDER BY rolname"
            )
            roles = cursor.fetchall()
            cursor.execute(
                "SELECT tableowner FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename = 'identity_product'"
            )
            owner = cursor.fetchone()[0]
        self.assertEqual(len(roles), 2)
        self.assertTrue(
            all(
                not superuser and not bypass and not schema_member
                for _, superuser, bypass, schema_member in roles
            )
        )
        self.assertEqual(owner, "custocrm_schema")

    def test_app_role_is_fail_closed_and_scoped(self) -> None:
        with transaction.atomic():
            self._set_role("custocrm_runtime_app")
            self.assertEqual(Product.objects.count(), 0)

        with transaction.atomic():
            self._set_role("custocrm_runtime_app")
            set_local_tenant(self.first.id)
            self.assertEqual(list(Product.objects.values_list("code", flat=True)), ["first"])
            Product.objects.create(
                organization_id=self.first.id,
                code="created",
                name="Created",
            )
            self.assertEqual(Product.objects.filter(code="created").update(name="Updated"), 1)
            self.assertEqual(Product.objects.filter(code="created").delete()[0], 1)

        with self.assertRaises(DatabaseError), transaction.atomic():
            self._set_role("custocrm_runtime_app")
            set_local_tenant(self.first.id)
            Product.objects.create(
                organization_id=self.second.id,
                code="forged",
                name="Forged",
            )

    def test_app_role_writes_platform_audit_event_without_tenant_context(self) -> None:
        # Login-failed audit path: app role, no tenant context, organization NULL.
        # ORM create() issues INSERT ... RETURNING id, which also requires SELECT
        # visibility of the new row (tenancy.0007 policies).
        with transaction.atomic():
            self._set_role("custocrm_runtime_app")
            event = AuditEvent.objects.create(
                action="identity.login_failed",
                object_type="HumanUser",
                result=AuditResult.DENIED,
                correlation_id="rls-null-org-audit",
            )
            self.assertIsNotNone(event.pk)

        with transaction.atomic():
            self._set_role("custocrm_runtime_app")
            self.assertEqual(
                AuditEvent.objects.filter(organization__isnull=False).count(), 0
            )

    def test_cross_tenant_relation_is_rejected_by_database_trigger(self) -> None:
        with self.assertRaises(DatabaseError), transaction.atomic():
            self._set_role("custocrm_runtime_app")
            set_local_tenant(self.first.id)
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO products_productdepartment "
                    "(organization_id, product_id, department_id, created_at) "
                    "VALUES (%s, %s, %s, NOW())",
                    [self.first.id, self.first_product.id, self.second_department.id],
                )

    def test_cross_tenant_many_to_many_is_rejected(self) -> None:
        channel = Channel.objects.create(
            organization=self.first,
            code="rls-agent",
            name="RLS agent",
        )
        agent = AIAgent.objects.create(
            organization=self.first,
            channel=channel,
            name="RLS agent",
        )
        foreign_knowledge = Knowledge.objects.create(
            organization=self.second,
            title="Foreign knowledge",
        )

        with self.assertRaises(DatabaseError), transaction.atomic():
            self._set_role("custocrm_runtime_app")
            set_local_tenant(self.first.id)
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ai_aiagent_knowledge_items (aiagent_id, knowledge_id) "
                    "VALUES (%s, %s)",
                    [agent.id, foreign_knowledge.id],
                )

    def test_http_request_runs_with_runtime_role_and_tenant_middleware(self) -> None:
        client = TenantAPIClient()
        client.force_authenticate(self.user)
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE custocrm_runtime_app")
        try:
            own = client.get(
                f"/api/v1/organizations/{self.first.public_id}/company/products/"
            )
            foreign = client.get(
                f"/api/v1/organizations/{self.second.public_id}/company/products/"
            )
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")
        self.assertEqual(own.status_code, 200)
        self.assertEqual([item["code"] for item in own.json()["items"]], ["first"])
        self.assertEqual(foreign.status_code, 404)

    def test_platform_role_can_only_use_ingress_directory(self) -> None:
        with self.assertRaises(DatabaseError), transaction.atomic():
            self._set_role("custocrm_runtime_platform")
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM identity_product LIMIT 1")

        with transaction.atomic():
            self._set_role("custocrm_runtime_platform")
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT organization_id, resource_id "
                    "FROM custocrm.product_ingest_directory WHERE lookup_key = %s",
                    ["first-hash"],
                )
                row = cursor.fetchone()
        self.assertEqual(row, (self.first.id, self.first_product.id))

    def test_transaction_local_context_clears_after_commit_and_rollback(self) -> None:
        with transaction.atomic():
            set_local_tenant(self.first.id)
            self.assertEqual(current_tenant_id(), self.first.id)
        self.assertIsNone(current_tenant_id())

        try:
            with transaction.atomic():
                set_local_tenant(self.second.id)
                self.assertEqual(current_tenant_id(), self.second.id)
                raise RuntimeError("rollback")
        except RuntimeError:
            pass
        self.assertIsNone(current_tenant_id())
