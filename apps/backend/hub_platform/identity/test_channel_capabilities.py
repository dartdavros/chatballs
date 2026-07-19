"""SPEC-HUB-0027 §5 — capability каналов и миграция прав по существующим ai.*."""

import importlib

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from hub_platform.identity.access_services import allowed_profile_scopes
from hub_platform.identity.capabilities import (
    CAPABILITY_REGISTRY,
    PROTECTED_CAPABILITIES,
    ScopeType,
)
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    Department,
    EmployeeAccessAssignment,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.identity.policy import ResourceScope, authorize

CHANNELS_VIEW = "channels.view"
CHANNELS_MANAGE = "channels.manage"


class ChannelCapabilityRegistryTests(TestCase):
    """§5.1 — обе capability назначаемы и допускают оба scope."""

    def test_registry_declares_both_scopes_and_is_assignable(self) -> None:
        for code in (CHANNELS_VIEW, CHANNELS_MANAGE):
            with self.subTest(code=code):
                spec = CAPABILITY_REGISTRY[code]
                self.assertEqual(
                    spec.allowed_scopes,
                    frozenset({ScopeType.ORGANIZATION, ScopeType.DEPARTMENT}),
                )
                self.assertTrue(spec.assignable)
                self.assertNotIn(code, PROTECTED_CAPABILITIES)

    def test_channel_capabilities_do_not_narrow_profile_scopes(self) -> None:
        # §5.3: набор допустимых scope профиля — пересечение по его capability.
        # Если бы channels.* были organization-only, department-назначения
        # существующих ai-профилей стали бы невалидными при выкате.
        self.assertEqual(
            allowed_profile_scopes(["ai.view", "ai.manage"]),
            allowed_profile_scopes(
                ["ai.view", "ai.manage", CHANNELS_VIEW, CHANNELS_MANAGE]
            ),
        )


class ChannelCapabilityScopeTests(TestCase):
    """§5.2 — фильтрация по scope канала, включая канал без отдела."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="example")
        self.sales = Department.objects.create(
            organization=self.organization, code="sales", name="Sales"
        )
        self.support = Department.objects.create(
            organization=self.organization, code="support", name="Support"
        )
        self.owner = self._employee("owner@example.test", EmployeeRole.OWNER)
        self.employee = self._employee("employee@example.test", EmployeeRole.EMPLOYEE)

    def _employee(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Specialist",
        )

    def _assign(self, *codes: str, department: Department | None = None) -> None:
        profile = AccessProfile.objects.create(
            organization=self.organization, name=f"Profile {'-'.join(codes)}"
        )
        for code in codes:
            AccessProfileCapability.objects.create(
                access_profile=profile, capability_code=code
            )
        EmployeeAccessAssignment.objects.create(
            employee=self.employee,
            access_profile=profile,
            scope_type=ScopeType.DEPARTMENT if department else ScopeType.ORGANIZATION,
            department=department,
            assigned_by=self.owner,
        )

    def test_department_scope_covers_only_its_own_department(self) -> None:
        self._assign(CHANNELS_VIEW, department=self.sales)

        self.assertTrue(
            authorize(
                self.employee,
                CHANNELS_VIEW,
                ResourceScope(self.organization.id, self.sales.id),
            )
        )
        self.assertFalse(
            authorize(
                self.employee,
                CHANNELS_VIEW,
                ResourceScope(self.organization.id, self.support.id),
            )
        )

    def test_channel_without_department_needs_organization_scope(self) -> None:
        # §5.2: канал без отдела виден только organization-scoped channels.view —
        # department-scoped сотрудник не получает его ни списком, ни по ID.
        self._assign(CHANNELS_VIEW, department=self.sales)
        self.assertFalse(
            authorize(
                self.employee, CHANNELS_VIEW, ResourceScope(self.organization.id, None)
            )
        )

    def test_organization_scope_covers_channels_with_and_without_department(self) -> None:
        self._assign(CHANNELS_VIEW, CHANNELS_MANAGE)

        for department_id in (self.sales.id, self.support.id, None):
            with self.subTest(department_id=department_id):
                self.assertTrue(
                    authorize(
                        self.employee,
                        CHANNELS_MANAGE,
                        ResourceScope(self.organization.id, department_id),
                    )
                )

    def test_ai_capability_no_longer_authorizes_channels(self) -> None:
        # ADR-HUB-0037 §9: право настраивать AI больше не даёт прав на канал.
        self._assign("ai.view", "ai.manage")
        self.assertFalse(
            authorize(
                self.employee, CHANNELS_VIEW, ResourceScope(self.organization.id, None)
            )
        )


class ChannelCapabilityMigrationTests(TransactionTestCase):
    """§5.3 — выдача channels.* по существующим ai.* без потери доступа."""

    migrate_from = [("identity", "0015_organization_status")]
    migrate_to = [("identity", "0016_channel_capabilities")]

    def setUp(self) -> None:
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        Organization = old_apps.get_model("identity", "Organization")
        AccessProfile = old_apps.get_model("identity", "AccessProfile")
        AccessProfileCapability = old_apps.get_model("identity", "AccessProfileCapability")

        organization = Organization.objects.create(name="Edevs", slug="edevs")
        other = Organization.objects.create(name="Other", slug="other")

        def profile(org, name: str, *codes: str) -> int:
            row = AccessProfile.objects.create(organization=org, name=name)
            for code in codes:
                AccessProfileCapability.objects.create(
                    access_profile=row, organization=org, capability_code=code
                )
            return row.pk

        self.editor_id = profile(organization, "AI editor", "ai.view", "ai.manage")
        self.reader_id = profile(organization, "AI reader", "ai.view")
        self.operator_id = profile(organization, "Operator", "conversations.view")
        self.other_editor_id = profile(other, "AI editor", "ai.view", "ai.manage")
        self.organization_id = organization.pk
        self.other_organization_id = other.pk

    def tearDown(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def _codes(self, apps, profile_id: int) -> set[str]:
        AccessProfileCapability = apps.get_model("identity", "AccessProfileCapability")
        return set(
            AccessProfileCapability.objects.filter(
                access_profile_id=profile_id
            ).values_list("capability_code", flat=True)
        )

    def test_forward_grants_channel_capabilities_by_ai_capabilities(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps

        self.assertEqual(
            self._codes(new_apps, self.editor_id),
            {"ai.view", "ai.manage", CHANNELS_VIEW, CHANNELS_MANAGE},
        )
        # ai.view без ai.manage даёт только просмотр: доступ не расширяется.
        self.assertEqual(
            self._codes(new_apps, self.reader_id), {"ai.view", CHANNELS_VIEW}
        )
        self.assertEqual(self._codes(new_apps, self.operator_id), {"conversations.view"})

    def test_forward_keeps_capability_rows_in_their_own_organization(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        AccessProfileCapability = new_apps.get_model("identity", "AccessProfileCapability")

        # organization_id обязателен и обязан совпадать с владельцем профиля:
        # триггер custocrm.enforce_tenant_fk отвергает расхождение.
        for profile_id, organization_id in (
            (self.editor_id, self.organization_id),
            (self.other_editor_id, self.other_organization_id),
        ):
            with self.subTest(profile_id=profile_id):
                rows = AccessProfileCapability.objects.filter(
                    access_profile_id=profile_id,
                    capability_code__in=(CHANNELS_VIEW, CHANNELS_MANAGE),
                )
                self.assertEqual(rows.count(), 2)
                self.assertEqual(
                    set(rows.values_list("organization_id", flat=True)),
                    {organization_id},
                )

    def test_grant_is_idempotent(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        AccessProfileCapability = new_apps.get_model("identity", "AccessProfileCapability")
        before = AccessProfileCapability.objects.count()

        migration = importlib.import_module(
            "hub_platform.identity.migrations.0016_channel_capabilities"
        )
        migration.grant_channel_capabilities(new_apps, None)

        self.assertEqual(AccessProfileCapability.objects.count(), before)

    def test_reverse_removes_granted_rows_before_restoring_constraint(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)

        # Откат обязан пройти целиком: если бы строки channels.* пережили
        # RunPython, восстановление прежнего check-constraint упало бы.
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        self.assertEqual(self._codes(old_apps, self.editor_id), {"ai.view", "ai.manage"})
        AccessProfileCapability = old_apps.get_model("identity", "AccessProfileCapability")
        self.assertFalse(
            AccessProfileCapability.objects.filter(
                capability_code__in=(CHANNELS_VIEW, CHANNELS_MANAGE)
            ).exists()
        )
