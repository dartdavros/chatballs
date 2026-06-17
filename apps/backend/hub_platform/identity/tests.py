import json

from django.test import Client, TestCase

from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import (
    AuditEvent,
    Department,
    EmployeeProfile,
    EmployeeRole,
    HumanUser,
    Organization,
    Product,
)
from hub_platform.identity.permissions import can_access_global_settings, can_access_sales_workspace


class BootstrapOwnerTests(TestCase):
    def test_bootstrap_creates_edevs_foundation(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
            full_name="Owner",
        )

        self.assertTrue(result.created_owner)
        self.assertEqual(Organization.objects.get().slug, "edevs")
        self.assertEqual(Department.objects.get().code, "sales")
        self.assertEqual(set(Product.objects.values_list("code", flat=True)), {"firepage", "foxray"})
        self.assertEqual(result.owner.employee_profile.role, EmployeeRole.OWNER)
        self.assertTrue(result.owner.employee_profile.totp_required)
        self.assertTrue(AuditEvent.objects.filter(action="identity.owner_bootstrapped").exists())

    def test_bootstrap_is_idempotent_for_owner(self) -> None:
        first = bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        second = bootstrap_edevs_owner(email="owner@edevs.tech", password="another-password")

        self.assertTrue(first.created_owner)
        self.assertFalse(second.created_owner)
        self.assertEqual(HumanUser.objects.count(), 1)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Product.objects.count(), 2)


class PermissionTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.sales = Department.objects.get(code="sales")

    def test_owner_can_access_global_settings_and_sales_workspace(self) -> None:
        owner = HumanUser.objects.get(email="owner@edevs.tech")

        self.assertTrue(can_access_global_settings(owner))
        self.assertTrue(can_access_sales_workspace(owner))

    def test_operator_cannot_access_global_settings(self) -> None:
        operator = HumanUser.objects.create_user(email="operator@edevs.tech", password="temporary-password")
        EmployeeProfile.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.OPERATOR,
            department=self.sales,
            must_change_password=True,
        )

        self.assertFalse(can_access_global_settings(operator))
        self.assertTrue(can_access_sales_workspace(operator))


class AuthEndpointTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = Client()

    def test_login_returns_session_payload(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "owner@edevs.tech", "password": "temporary-password"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["user"]["role"], EmployeeRole.OWNER)

    def test_login_rejects_invalid_password(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "owner@edevs.tech", "password": "wrong-password"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertTrue(AuditEvent.objects.filter(action="identity.login_failed").exists())

    def test_change_temporary_password_clears_profile_flag(self) -> None:
        owner = HumanUser.objects.get(email="owner@edevs.tech")
        profile = owner.employee_profile
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])
        self.client.login(username="owner@edevs.tech", password="temporary-password")

        response = self.client.post(
            "/api/v1/auth/change-temporary-password/",
            data=json.dumps(
                {
                    "currentPassword": "temporary-password",
                    "newPassword": "new-temporary-password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertFalse(profile.must_change_password)
