import json

from django.test import Client, TestCase

from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.auth_views import _totp_code
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
        self.assertTrue(result.owner.is_staff)
        self.assertTrue(result.owner.is_superuser)
        operator = HumanUser.objects.get(email="a.kotova@edevs.tech")
        self.assertEqual(operator.full_name, "Анна Котова")
        self.assertEqual(operator.employee_profile.role, EmployeeRole.OPERATOR)
        self.assertEqual(operator.employee_profile.phone, "+7 916 245 14 02")
        self.assertTrue(AuditEvent.objects.filter(action="identity.owner_bootstrapped").exists())

    def test_bootstrap_is_idempotent_for_owner(self) -> None:
        first = bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        second = bootstrap_edevs_owner(email="owner@edevs.tech", password="another-password")

        self.assertTrue(first.created_owner)
        self.assertFalse(second.created_owner)
        self.assertEqual(HumanUser.objects.count(), 2)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Product.objects.count(), 2)

    def test_bootstrap_promotes_existing_owner_to_django_admin_access(self) -> None:
        user = HumanUser.objects.create_user(email="owner@edevs.tech", password="temporary-password")

        result = bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")

        user.refresh_from_db()
        self.assertFalse(result.created_owner)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


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
        self.assertEqual(payload["user"]["organizationName"], "Edevs")
        self.assertEqual(payload["user"]["role"], EmployeeRole.OWNER)

    def test_session_sets_csrf_cookie_for_spa(self) -> None:
        response = self.client.get("/api/v1/auth/session/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

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

    def test_totp_setup_and_confirm_enables_profile_totp(self) -> None:
        self.client.login(username="owner@edevs.tech", password="temporary-password")

        setup_response = self.client.get("/api/v1/auth/totp/setup/")

        self.assertEqual(setup_response.status_code, 200)
        secret = setup_response.json()["secret"]
        self.assertTrue(secret)
        self.assertIn("otpauth://totp/", setup_response.json()["otpauthUrl"])

        confirm_response = self.client.post(
            "/api/v1/auth/totp/confirm/",
            data=json.dumps({"code": _totp_code(secret)}),
            content_type="application/json",
        )

        self.assertEqual(confirm_response.status_code, 200)
        owner = HumanUser.objects.get(email="owner@edevs.tech")
        self.assertTrue(owner.employee_profile.totp_enabled)

    def test_enabled_totp_requires_second_factor_before_session(self) -> None:
        owner = HumanUser.objects.get(email="owner@edevs.tech")
        profile = owner.employee_profile
        profile.totp_secret = "JBSWY3DPEHPK3PXP"
        profile.totp_enabled = True
        profile.save(update_fields=["totp_secret", "totp_enabled"])

        login_response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "owner@edevs.tech", "password": "temporary-password"}),
            content_type="application/json",
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertFalse(login_response.json()["authenticated"])
        self.assertTrue(login_response.json()["totpRequired"])

        verify_response = self.client.post(
            "/api/v1/auth/totp/verify/",
            data=json.dumps({"code": _totp_code(profile.totp_secret)}),
            content_type="application/json",
        )

        self.assertEqual(verify_response.status_code, 200)
        self.assertTrue(verify_response.json()["authenticated"])


class DjangoAdminTests(TestCase):
    def test_bootstrapped_owner_can_access_django_admin(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        client = Client()
        self.assertTrue(client.login(username="owner@edevs.tech", password="temporary-password"))

        response = client.get("/admin/")

        self.assertEqual(response.status_code, 200)


class EmployeeEndpointTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.sales = Department.objects.get(code="sales")
        self.client = Client()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_owner_creates_operator_with_temporary_password(self) -> None:
        response = self.client.post(
            "/api/v1/employees/operators/",
            data=json.dumps(
                {
                    "email": "operator@edevs.tech",
                    "fullName": "Operator",
                    "temporaryPassword": "operator-password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        operator = HumanUser.objects.get(email="operator@edevs.tech")
        self.assertTrue(operator.check_password("operator-password"))
        self.assertEqual(operator.employee_profile.role, EmployeeRole.OPERATOR)
        self.assertTrue(operator.employee_profile.must_change_password)
        self.assertTrue(AuditEvent.objects.filter(action="identity.operator_created").exists())

    def test_operator_cannot_create_operator(self) -> None:
        operator = HumanUser.objects.create_user(email="operator@edevs.tech", password="operator-password")
        EmployeeProfile.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.OPERATOR,
            department=self.sales,
        )
        self.client.logout()
        self.client.login(username="operator@edevs.tech", password="operator-password")

        response = self.client.post(
            "/api/v1/employees/operators/",
            data=json.dumps(
                {
                    "email": "another@edevs.tech",
                    "temporaryPassword": "operator-password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(AuditEvent.objects.filter(action="identity.owner_permission_denied").exists())

    def test_owner_blocks_operator(self) -> None:
        operator = HumanUser.objects.create_user(email="operator@edevs.tech", password="operator-password")
        EmployeeProfile.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.OPERATOR,
            department=self.sales,
        )

        response = self.client.post(f"/api/v1/employees/{operator.id}/block/")

        self.assertEqual(response.status_code, 200)
        operator.refresh_from_db()
        self.assertFalse(operator.is_active)
        self.assertTrue(operator.employee_profile.is_blocked)
        self.assertTrue(AuditEvent.objects.filter(action="identity.operator_blocked").exists())

    def test_owner_updates_operator_card_fields(self) -> None:
        operator = HumanUser.objects.get(email="a.kotova@edevs.tech")

        response = self.client.post(
            f"/api/v1/employees/{operator.id}/update/",
            data=json.dumps(
                {
                    "fullName": "Анна Котова",
                    "email": "anna.kotova@edevs.tech",
                    "phone": "+7 916 245 14 03",
                    "role": EmployeeRole.OPERATOR,
                    "department": "sales",
                    "totpEnabled": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        operator.refresh_from_db()
        operator.employee_profile.refresh_from_db()
        self.assertEqual(operator.email, "anna.kotova@edevs.tech")
        self.assertEqual(operator.employee_profile.phone, "+7 916 245 14 03")
        self.assertTrue(operator.employee_profile.totp_enabled)

    def test_owner_resets_operator_password(self) -> None:
        operator = HumanUser.objects.get(email="a.kotova@edevs.tech")

        response = self.client.post(f"/api/v1/employees/{operator.id}/reset-password/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        operator.refresh_from_db()
        operator.employee_profile.refresh_from_db()
        self.assertTrue(operator.check_password(payload["temporaryPassword"]))
        self.assertTrue(operator.employee_profile.must_change_password)

    def test_owner_unblocks_operator(self) -> None:
        operator = HumanUser.objects.get(email="a.kotova@edevs.tech")
        operator.employee_profile.block()

        response = self.client.post(f"/api/v1/employees/{operator.id}/unblock/")

        self.assertEqual(response.status_code, 200)
        operator.refresh_from_db()
        operator.employee_profile.refresh_from_db()
        self.assertTrue(operator.is_active)
        self.assertFalse(operator.employee_profile.is_blocked)


class CompanyEndpointTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.sales = Department.objects.get(code="sales")
        self.client = Client()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_owner_reads_departments_and_products(self) -> None:
        departments_response = self.client.get("/api/v1/company/departments/")
        products_response = self.client.get("/api/v1/company/products/")

        self.assertEqual(departments_response.status_code, 200)
        self.assertEqual(products_response.status_code, 200)
        self.assertEqual(departments_response.json()["items"][0]["code"], "sales")
        self.assertEqual(
            set(product["code"] for product in products_response.json()["items"]),
            {"firepage", "foxray"},
        )

    def test_owner_creates_and_deactivates_product(self) -> None:
        create_response = self.client.post(
            "/api/v1/company/products/create/",
            data=json.dumps({"code": "academy", "name": "Academy"}),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 201)
        product_id = create_response.json()["product"]["id"]

        deactivate_response = self.client.post(f"/api/v1/company/products/{product_id}/deactivate/")

        self.assertEqual(deactivate_response.status_code, 200)
        self.assertEqual(deactivate_response.json()["product"]["status"], "DISABLED")
        self.assertTrue(AuditEvent.objects.filter(action="identity.product_created").exists())
        self.assertTrue(AuditEvent.objects.filter(action="identity.product_deactivated").exists())

    def test_operator_cannot_create_product(self) -> None:
        operator = HumanUser.objects.create_user(email="operator@edevs.tech", password="operator-password")
        EmployeeProfile.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.OPERATOR,
            department=self.sales,
        )
        self.client.logout()
        self.client.login(username="operator@edevs.tech", password="operator-password")

        response = self.client.post(
            "/api/v1/company/products/create/",
            data=json.dumps({"code": "academy", "name": "Academy"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
