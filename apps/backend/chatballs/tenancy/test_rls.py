from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.ai.models import AIAgent, Knowledge
from chatballs.channels.models import Channel
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.invitation_models import OrganizationInvitation
from chatballs.identity.invitation_service import (
    invitation_preview,
    issue_invitation,
    pending_invitation_for_token,
)
from chatballs.identity.models import (
    AuditEvent,
    AuditResult,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.tenancy.database import current_tenant_id, set_local_tenant, tenant_atomic
from chatballs.tenancy.lookup import reserve_organization_id
from chatballs.tenancy.models import StorageReservation
from chatballs.testing import TenantAPIClient


class RowLevelSecurityTests(TransactionTestCase):

    reset_sequences = True



    def setUp(self) -> None:

        self.first = Organization.objects.create(name="First", slug="rls-first")

        self.second = Organization.objects.create(name="Second", slug="rls-second")

        self.first_group = EmployeeGroup.objects.create(

            organization=self.first,

            name="First",

        )

        self.second_group = EmployeeGroup.objects.create(

            organization=self.second,

            name="Foreign",

        )

        self.user = HumanUser.objects.create_user(email="rls@example.test")

        self.membership = OrganizationMembership.objects.create(

            organization=self.first,

            user=self.user,

            role=EmployeeRole.OWNER,

            position_title="Owner",

        )



    @staticmethod

    def _set_role(role: str) -> None:

        if role not in {"chatballs_runtime_app", "chatballs_runtime_platform"}:

            raise ValueError("Unexpected test role")

        with connection.cursor() as cursor:

            cursor.execute(f"SET LOCAL ROLE {role}")



    def test_runtime_roles_are_not_owners_or_bypassrls(self) -> None:

        with connection.cursor() as cursor:

            cursor.execute(

                "SELECT rolname, rolsuper, rolbypassrls, "

                "pg_has_role(rolname, 'chatballs_schema', 'MEMBER') FROM pg_roles "

                "WHERE rolname IN ('chatballs_runtime_app', 'chatballs_runtime_platform') "

                "ORDER BY rolname"

            )

            roles = cursor.fetchall()

            cursor.execute(

                "SELECT tableowner FROM pg_tables "

                "WHERE schemaname = 'public' AND tablename = 'identity_employeegroup'"

            )

            owner = cursor.fetchone()[0]

        self.assertEqual(len(roles), 2)

        self.assertTrue(

            all(

                not superuser and not bypass and not schema_member

                for _, superuser, bypass, schema_member in roles

            )

        )

        self.assertEqual(owner, "chatballs_schema")



    def test_app_role_is_fail_closed_and_scoped(self) -> None:

        with transaction.atomic():

            self._set_role("chatballs_runtime_app")

            self.assertEqual(EmployeeGroup.objects.count(), 0)



        with transaction.atomic():

            self._set_role("chatballs_runtime_app")

            set_local_tenant(self.first.id)

            self.assertEqual(

                list(EmployeeGroup.objects.values_list("name", flat=True)), ["First"]

            )

            EmployeeGroup.objects.create(

                organization_id=self.first.id,

                name="Created",

            )

            self.assertEqual(

                EmployeeGroup.objects.filter(name="Created").update(color="#123456"), 1

            )

            self.assertEqual(EmployeeGroup.objects.filter(name="Created").delete()[0], 1)



        # Чужая организация в контексте первой не видна вовсе (tenancy/0033):
        # проверка внешнего ключа в full_clean отказывает ещё до INSERT.
        with self.assertRaises((DatabaseError, ValidationError)), transaction.atomic():

            self._set_role("chatballs_runtime_app")

            set_local_tenant(self.first.id)

            EmployeeGroup.objects.create(

                organization_id=self.second.id,

                name="Forged",

            )



    def test_app_role_updates_only_current_organization(self) -> None:

        with transaction.atomic():

            self._set_role("chatballs_runtime_app")

            set_local_tenant(self.first.id)

            self.assertEqual(

                Organization.objects.filter(id=self.first.id).update(

                    name="Updated first"

                ),

                1,

            )

            self.assertEqual(

                Organization.objects.filter(id=self.second.id).update(

                    name="Forged second"

                ),

                0,

            )



        self.first.refresh_from_db()

        self.second.refresh_from_db()

        self.assertEqual(self.first.name, "Updated first")

        self.assertEqual(self.second.name, "Second")



    def test_app_role_manages_only_own_storage_reservations(self) -> None:

        with transaction.atomic():

            self._set_role("chatballs_runtime_app")

            set_local_tenant(self.first.id)

            reservation = StorageReservation.objects.create(

                organization=self.first,

                idempotency_key="rls-storage",

                reserved_bytes=128,

            )

            self.assertIsNotNone(reservation.pk)

            self.assertEqual(

                StorageReservation.objects.filter(organization=self.second).count(),

                0,

            )



        with self.assertRaises(DatabaseError), transaction.atomic():

            self._set_role("chatballs_runtime_app")

            set_local_tenant(self.first.id)

            StorageReservation.objects.create(

                organization=self.second,

                idempotency_key="rls-forged-storage",

                reserved_bytes=128,

            )



    def test_app_role_writes_platform_audit_event_without_tenant_context(self) -> None:

        # Login-failed audit path: app role, no tenant context, organization NULL.

        # ORM create() issues INSERT ... RETURNING id, which also requires SELECT

        # visibility of the new row (tenancy.0007 policies).

        with transaction.atomic():

            self._set_role("chatballs_runtime_app")

            event = AuditEvent.objects.create(

                action="identity.login_failed",

                object_type="HumanUser",

                result=AuditResult.DENIED,

                correlation_id="rls-null-org-audit",

            )

            self.assertIsNotNone(event.pk)



        with transaction.atomic():

            self._set_role("chatballs_runtime_app")

            self.assertEqual(

                AuditEvent.objects.filter(organization__isnull=False).count(), 0

            )



    def test_cross_tenant_relation_is_rejected_by_database_trigger(self) -> None:

        with self.assertRaises(DatabaseError), transaction.atomic():

            self._set_role("chatballs_runtime_app")

            set_local_tenant(self.first.id)

            with connection.cursor() as cursor:

                cursor.execute(

                    "INSERT INTO identity_employeegroupmember "

                    "(organization_id, group_id, employee_id, created_at) "

                    "VALUES (%s, %s, %s, NOW())",

                    [self.first.id, self.second_group.id, self.membership.id],

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

            category=ensure_uncategorized_category(self.second),

            title="Foreign knowledge",

        )



        with self.assertRaises(DatabaseError), transaction.atomic():

            self._set_role("chatballs_runtime_app")

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

            cursor.execute("SET ROLE chatballs_runtime_app")

        try:

            own = client.get(

                f"/api/v1/organizations/{self.first.public_id}/company/groups/"

            )

            foreign = client.get(

                f"/api/v1/organizations/{self.second.public_id}/company/groups/"

            )

        finally:

            with connection.cursor() as cursor:

                cursor.execute("RESET ROLE")

        self.assertEqual(own.status_code, 200)

        self.assertEqual([item["name"] for item in own.json()["items"]], ["First"])

        self.assertEqual(foreign.status_code, 404)



    def test_app_role_reads_ingress_directory_and_adds_organizations_only_in_context(self) -> None:
        # Каталоги входа доступны роли app (tenancy/0032): backend-app
        # обходится без platform-соединения.
        with transaction.atomic():
            self._set_role("chatballs_runtime_app")
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT organization_id FROM chatballs.membership_directory "
                    "WHERE user_id = %s",
                    [self.user.id],
                )
                self.assertEqual(cursor.fetchone()[0], self.first.id)
        # Без контекста INSERT организации для app закрыт (tenancy/0035).
        with self.assertRaises(DatabaseError), transaction.atomic():
            self._set_role("chatballs_runtime_app")
            Organization.objects.create(name="Third", slug="rls-third")
        # В контексте заранее выделенного id — открыт: так работает кнопка
        # «Добавить организацию» (identity.organization_creation).
        with transaction.atomic():
            self._set_role("chatballs_runtime_app")
            organization_id = reserve_organization_id()
            with tenant_atomic(organization_id):
                Organization(id=organization_id, name="Third", slug="rls-third").save(force_insert=True)
                self.assertEqual(Organization.objects.get(pk=organization_id).slug, "rls-third")
        self.assertTrue(Organization.objects.filter(slug="rls-third").exists())
        # Чужой контекст не подходит: id строки обязан совпасть с контекстом.
        with self.assertRaises(DatabaseError), transaction.atomic():
            self._set_role("chatballs_runtime_app")
            with tenant_atomic(self.first.id):
                Organization(id=reserve_organization_id(), name="Fourth", slug="rls-fourth").save(force_insert=True)

    def test_app_role_finds_invitation_by_token_without_context(self) -> None:
        # Ссылка /join открывается без контекста: приглашение находит каталог
        # invitation_directory (tenancy/0035), иначе роль app видела бы пустоту.
        issued = issue_invitation(
            organization=self.second,
            email="invited@example.test",
            role=EmployeeRole.EMPLOYEE,
            expires_at=timezone.now() + timedelta(days=1),
            created_by=None,
        )
        with transaction.atomic():
            self._set_role("chatballs_runtime_app")
            self.assertEqual(OrganizationInvitation.objects.count(), 0)
            invitation = pending_invitation_for_token(issued.token)
            self.assertIsNotNone(invitation)
            self.assertEqual(invitation.id, issued.invitation.id)
            self.assertEqual(invitation.organization.slug, "rls-second")
            self.assertIsNone(pending_invitation_for_token("wrong-token"))
            preview = invitation_preview(issued.token)
            self.assertEqual(preview["organizationName"], "Second")

    def test_platform_role_can_only_use_ingress_directory(self) -> None:

        with self.assertRaises(DatabaseError), transaction.atomic():

            self._set_role("chatballs_runtime_platform")

            with connection.cursor() as cursor:

                cursor.execute("SELECT id FROM identity_employeegroup LIMIT 1")



        # Ingress-вьюха продаж удалена (ADR-CHATBALLS-0041) — используем membership_directory.

        with transaction.atomic():

            self._set_role("chatballs_runtime_platform")

            with connection.cursor() as cursor:

                cursor.execute(

                    "SELECT organization_id, resource_id "

                    "FROM chatballs.membership_directory WHERE user_id = %s",

                    [self.user.id],

                )

                row = cursor.fetchone()

        self.assertIsNotNone(row)

        self.assertEqual(row[0], self.first.id)



    def test_app_role_sees_organizations_only_in_their_context(self) -> None:
        # tenancy/0033: без контекста строк организаций нет, в контексте — своя.
        with transaction.atomic():
            self._set_role("chatballs_runtime_app")
            self.assertEqual(Organization.objects.count(), 0)
            set_local_tenant(self.first.id)
            self.assertEqual(
                list(Organization.objects.values_list("id", flat=True)), [self.first.id]
            )

    def test_app_role_finds_organizations_through_the_directory(self) -> None:
        from chatballs.tenancy.lookup import (
            instance_has_organizations,
            iter_organizations,
            organization_by_public_id,
        )

        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            self.assertTrue(instance_has_organizations())
            self.assertEqual(
                [organization.id for organization in iter_organizations()],
                [self.first.id, self.second.id],
            )
            found = organization_by_public_id(self.second.public_id)
            self.assertIsNotNone(found)
            self.assertEqual(found.id, self.second.id)
            # Сессия собирает членства по каталогу и читает каждую организацию
            # в её контексте.
            client = TenantAPIClient()
            client.force_authenticate(self.user)
            session = client.get("/api/v1/auth/session/").json()
            self.assertEqual(
                [item["organizationPublicId"] for item in session["user"]["memberships"]],
                [str(self.first.public_id)],
            )
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")

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

