from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MembershipMigrationTests(TransactionTestCase):
    migrate_from = [("identity", "0011_enforce_capability_registry")]
    migrate_to = [("identity", "0012_membership_identity")]

    def setUp(self) -> None:
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        Organization = old_apps.get_model("identity", "Organization")
        HumanUser = old_apps.get_model("identity", "HumanUser")
        EmployeeProfile = old_apps.get_model("identity", "EmployeeProfile")
        AccessProfile = old_apps.get_model("identity", "AccessProfile")
        EmployeeAccessAssignment = old_apps.get_model(
            "identity", "EmployeeAccessAssignment"
        )

        organization = Organization.objects.create(name="Acme", slug="acme")
        owner_user = HumanUser.objects.create(email="owner@example.test", password="hash")
        employee_user = HumanUser.objects.create(email="employee@example.test", password="hash")
        owner = EmployeeProfile.objects.create(
            user=owner_user,
            organization=organization,
            role="OWNER",
            position_title="Owner",
        )
        employee = EmployeeProfile.objects.create(
            user=employee_user,
            organization=organization,
            role="EMPLOYEE",
            position_title="Specialist",
            must_change_password=True,
            totp_enabled=True,
            totp_secret="JBSWY3DPEHPK3PXP",
        )
        access_profile = AccessProfile.objects.create(
            organization=organization,
            name="Sales",
        )
        assignment = EmployeeAccessAssignment.objects.create(
            employee=employee,
            access_profile=access_profile,
            scope_type="ORGANIZATION",
            assigned_by=owner,
        )
        self.organization_id = organization.pk
        self.employee_user_id = employee_user.pk
        self.membership_id = employee.pk
        self.assignment_id = assignment.pk

    def tearDown(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_forward_migration_preserves_identity_primary_keys_and_access(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps

        Organization = new_apps.get_model("identity", "Organization")
        HumanUser = new_apps.get_model("identity", "HumanUser")
        OrganizationMembership = new_apps.get_model(
            "identity", "OrganizationMembership"
        )
        EmployeeAccessAssignment = new_apps.get_model(
            "identity", "EmployeeAccessAssignment"
        )

        organization = Organization.objects.get(pk=self.organization_id)
        user = HumanUser.objects.get(pk=self.employee_user_id)
        membership = OrganizationMembership.objects.get(pk=self.membership_id)
        assignment = EmployeeAccessAssignment.objects.get(pk=self.assignment_id)

        self.assertIsNotNone(organization.public_id)
        self.assertEqual(membership.pk, self.membership_id)
        self.assertEqual(membership.user_id, self.employee_user_id)
        self.assertEqual(assignment.employee_id, self.membership_id)
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.totp_enabled)
        self.assertEqual(user.totp_secret, "JBSWY3DPEHPK3PXP")
