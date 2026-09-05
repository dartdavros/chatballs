import json
from unittest import mock

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.backends.db import SessionStore
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from chatballs.testing import TenantAPIClient as APIClient
from rest_framework.throttling import ScopedRateThrottle

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.auth.totp_utils import _totp_code
from chatballs.identity.models import (
    AuditEvent,
    EmployeeGroup,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.identity.policy import ResourceScope, authorize
from chatballs.products.models import Product

_LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


class BootstrapOwnerTests(TestCase):
    def test_bootstrap_creates_foundation(self) -> None:
        result = bootstrap_owner(
            email="owner@example.com",
            password="temporary-password",
            full_name="Owner",
        )

        self.assertTrue(result.created_owner)
        self.assertEqual(Organization.objects.get().slug, "demo")
        # Seed создаёт стартовые группы (ADR-HUB-0043).
        self.assertEqual(
            set(EmployeeGroup.objects.values_list("name", flat=True)),
            {"Операторы", "Поддержка"},
        )
        self.assertEqual(result.support_group.name, "Поддержка")
        self.assertEqual(set(Product.objects.values_list("code", flat=True)), {"site", "app"})
        self.assertEqual(result.owner.memberships.get().role, EmployeeRole.OWNER)
        # TOTP выключен по умолчанию (намеренно, локальная разработка).
        self.assertFalse(result.owner.memberships.get().totp_required)
        self.assertTrue(result.owner.is_staff)
        self.assertTrue(result.owner.is_superuser)
        operator = HumanUser.objects.get(email="staff.member@example.org")
        self.assertEqual(operator.full_name, "Анна Котова")
        self.assertEqual(operator.memberships.get().role, EmployeeRole.EMPLOYEE)
        self.assertEqual(operator.memberships.get().phone, "+7 916 245 14 02")
        self.assertEqual(
            [link.group.name for link in operator.memberships.get().group_links.all()],
            ["Операторы"],
        )
        self.assertTrue(AuditEvent.objects.filter(action="identity.owner_bootstrapped").exists())

    def test_bootstrap_is_idempotent_for_owner(self) -> None:
        first = bootstrap_owner(email="owner@example.com", password="temporary-password")
        second = bootstrap_owner(email="owner@example.com", password="another-password")

        self.assertTrue(first.created_owner)
        self.assertFalse(second.created_owner)
        self.assertEqual(HumanUser.objects.count(), 2)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Product.objects.count(), 2)

    def test_bootstrap_promotes_existing_owner_to_django_admin_access(self) -> None:
        user = HumanUser.objects.create_user(email="owner@example.com", password="temporary-password")

        result = bootstrap_owner(email="owner@example.com", password="temporary-password")

        user.refresh_from_db()
        self.assertFalse(result.created_owner)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class PermissionTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")

    def test_owner_can_access_global_settings_and_sales_workspace(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        membership = owner.memberships.get(organization=self.organization)

        self.assertTrue(
            authorize(membership, "settings.manage", ResourceScope(self.organization.id))
        )
        self.assertTrue(
            authorize(
                membership,
                "conversations.view",
                ResourceScope(self.organization.id),
            )
        )

    def test_operator_cannot_access_global_settings(self) -> None:
        operator = HumanUser.objects.get(email="staff.member@example.org")
        membership = operator.memberships.get(organization=self.organization)
        self.assertFalse(
            authorize(membership, "settings.manage", ResourceScope(self.organization.id))
        )
        self.assertTrue(
            authorize(
                membership,
                "conversations.view",
                ResourceScope(self.organization.id),
            )
        )


class AuthEndpointTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.client = Client()

    def test_login_returns_session_payload(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "owner@example.com", "password": "temporary-password"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertNotIn("organizationName", payload["user"])
        self.assertNotIn("role", payload["user"])
        self.assertEqual(len(payload["user"]["memberships"]), 1)
        membership = payload["user"]["memberships"][0]
        self.assertIn("groups", membership)
        self.assertIn("employees.manage_privileged", membership["capabilities"])
        self.assertEqual(membership["organizationName"], "Demo")
        self.assertEqual(membership["role"], EmployeeRole.OWNER)

    def test_session_sets_csrf_cookie_for_spa(self) -> None:
        response = self.client.get("/api/v1/auth/session/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_login_rejects_invalid_password(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "owner@example.com", "password": "wrong-password"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertTrue(AuditEvent.objects.filter(action="identity.login_failed").exists())

    def test_password_reset_request_enqueues_outbox_event(self) -> None:
        from chatballs.events.models import OutboxEvent

        owner = HumanUser.objects.get(email="owner@example.com")
        response = self.client.post(
            "/api/v1/auth/password-reset/request/",
            data=json.dumps({"email": "owner@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        # Письмо отправляется воркером асинхронно, не в запросе.
        self.assertEqual(len(mail.outbox), 0)
        event = OutboxEvent.objects.get(event_type="identity.password_reset_requested")
        self.assertEqual(event.payload, {"userId": owner.id})
        self.assertTrue(AuditEvent.objects.filter(action="identity.password_reset_requested").exists())

    def test_password_reset_request_does_not_reveal_unknown_email(self) -> None:
        from chatballs.events.models import OutboxEvent

        response = self.client.post(
            "/api/v1/auth/password-reset/request/",
            data=json.dumps({"email": "nobody@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(OutboxEvent.objects.filter(event_type="identity.password_reset_requested").exists())

    def test_password_reset_handler_sends_email(self) -> None:
        from chatballs.identity.event_handlers import handle_password_reset_requested

        owner = HumanUser.objects.get(email="owner@example.com")
        handle_password_reset_requested({"userId": owner.id}, None)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("reset-password", mail.outbox[0].body)

    def _reset_link(self, email: str) -> tuple[str, str]:
        user = HumanUser.objects.get(email=email)
        return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)

    def test_password_reset_confirm_sets_new_password(self) -> None:
        uid, token = self._reset_link("owner@example.com")

        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            data=json.dumps({"uid": uid, "token": token, "newPassword": "Fresh-Pass-99"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertTrue(HumanUser.objects.get(email="owner@example.com").check_password("Fresh-Pass-99"))
        self.assertTrue(AuditEvent.objects.filter(action="identity.password_reset_completed").exists())

    def test_password_reset_confirm_rejects_invalid_token(self) -> None:
        uid, _ = self._reset_link("owner@example.com")

        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            data=json.dumps({"uid": uid, "token": "bad-token", "newPassword": "Fresh-Pass-99"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(HumanUser.objects.get(email="owner@example.com").check_password("Fresh-Pass-99"))

    def test_password_reset_validate_reflects_token_state(self) -> None:
        uid, token = self._reset_link("owner@example.com")

        valid = self.client.get(f"/api/v1/auth/password-reset/validate/?uid={uid}&token={token}")
        invalid = self.client.get(f"/api/v1/auth/password-reset/validate/?uid={uid}&token=bad-token")

        self.assertTrue(valid.json()["valid"])
        self.assertFalse(invalid.json()["valid"])

    def test_change_temporary_password_clears_user_flag(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        owner.must_change_password = True
        owner.save(update_fields=["must_change_password"])
        self.client.login(username="owner@example.com", password="temporary-password")

        response = self.client.post(
            "/api/v1/auth/change-temporary-password/",
            data=json.dumps(
                {
                    "currentPassword": "temporary-password",
                    "newPassword": "New-Temporary-99",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        owner.refresh_from_db()
        self.assertFalse(owner.must_change_password)

    def test_change_temporary_password_rejects_weak_password(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        owner.must_change_password = True
        owner.save(update_fields=["must_change_password"])
        self.client.login(username="owner@example.com", password="temporary-password")

        response = self.client.post(
            "/api/v1/auth/change-temporary-password/",
            data=json.dumps({"currentPassword": "temporary-password", "newPassword": "onlyletters"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        owner.refresh_from_db()
        self.assertTrue(owner.must_change_password)

    def test_profile_update_changes_current_user_identity(self) -> None:
        self.client.login(username="owner@example.com", password="temporary-password")

        response = self.client.post(
            "/api/v1/auth/profile/update/",
            data=json.dumps({"fullName": "Иван Петров", "email": "ivan@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        owner = HumanUser.objects.get(id=response.json()["user"]["id"])
        self.assertEqual(owner.full_name, "Иван Петров")
        self.assertEqual(owner.email, "ivan@example.com")
        self.assertTrue(AuditEvent.objects.filter(action="identity.profile_updated").exists())

    def test_profile_appearance_saves_theme_and_accent(self) -> None:
        """Тема и акцент — глобальные настройки пользователя (SPEC-HUB-0031 §7)."""
        self.client.login(username="owner@example.com", password="temporary-password")

        response = self.client.post(
            "/api/v1/auth/profile/appearance/",
            data=json.dumps({"theme": "DARK", "accent": "#0F9B8E"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["user"]
        self.assertEqual(payload["uiTheme"], "DARK")
        self.assertEqual(payload["uiAccent"], "#0f9b8e")
        owner = HumanUser.objects.get(email="owner@example.com")
        self.assertEqual(owner.ui_theme, "DARK")
        self.assertEqual(owner.ui_accent, "#0f9b8e")

        # Пустой акцент возвращает дефолтный синий на клиенте.
        cleared = self.client.post(
            "/api/v1/auth/profile/appearance/",
            data=json.dumps({"theme": "SYSTEM", "accent": ""}),
            content_type="application/json",
        )
        self.assertEqual(cleared.json()["user"]["uiAccent"], "")

        for body in ({"theme": "NEON"}, {"accent": "blue"}, {"accent": "#12345"}):
            with self.subTest(body=body):
                rejected = self.client.post(
                    "/api/v1/auth/profile/appearance/",
                    data=json.dumps(body),
                    content_type="application/json",
                )
                self.assertEqual(rejected.status_code, 400)

    def test_profile_password_changes_current_user_password(self) -> None:
        self.client.login(username="owner@example.com", password="temporary-password")

        response = self.client.post(
            "/api/v1/auth/profile/password/",
            data=json.dumps({"currentPassword": "temporary-password", "newPassword": "New-Profile-99"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        owner = HumanUser.objects.get(email="owner@example.com")
        self.assertTrue(owner.check_password("New-Profile-99"))
        self.assertTrue(AuditEvent.objects.filter(action="identity.profile_password_changed").exists())

    def test_profile_totp_start_marks_setup_required(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        profile = owner.memberships.get()
        profile.totp_required = False
        profile.save(update_fields=["totp_required"])
        owner.totp_enabled = False
        owner.totp_secret = "JBSWY3DPEHPK3PXP"
        owner.save(update_fields=["totp_enabled", "totp_secret"])
        self.client.login(username="owner@example.com", password="temporary-password")

        response = self.client.post("/api/v1/auth/profile/totp/start/")

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        owner.refresh_from_db()
        self.assertFalse(profile.totp_required)
        self.assertFalse(owner.totp_enabled)
        self.assertEqual(owner.totp_secret, "")

    def test_profile_totp_disable_requires_password_and_revokes_other_sessions(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        profile = owner.memberships.get()
        owner.totp_enabled = True
        owner.totp_secret = "JBSWY3DPEHPK3PXP"
        owner.save(update_fields=["totp_enabled", "totp_secret"])
        self.client.login(username="owner@example.com", password="temporary-password")
        other_session = SessionStore()
        other_session["_auth_user_id"] = str(owner.id)
        other_session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        other_session["_auth_user_hash"] = owner.get_session_auth_hash()
        other_session.save()

        response = self.client.post(
            "/api/v1/auth/profile/totp/disable/",
            data=json.dumps({"currentPassword": "temporary-password"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revoked"], 1)
        profile.refresh_from_db()
        owner.refresh_from_db()
        self.assertFalse(profile.totp_required)
        self.assertFalse(owner.totp_enabled)
        self.assertEqual(owner.totp_secret, "")

    def test_totp_setup_and_confirm_enables_profile_totp(self) -> None:
        # TOTP по умолчанию не требуется; включаем требование, чтобы пройти setup→confirm.
        owner = HumanUser.objects.get(email="owner@example.com")
        profile = owner.memberships.get()
        profile.totp_required = True
        profile.save(update_fields=["totp_required"])
        self.client.login(username="owner@example.com", password="temporary-password")

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
        owner = HumanUser.objects.get(email="owner@example.com")
        self.assertTrue(owner.totp_enabled)

    def test_enabled_totp_requires_second_factor_before_session(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        owner.totp_secret = "JBSWY3DPEHPK3PXP"
        owner.totp_enabled = True
        owner.save(update_fields=["totp_secret", "totp_enabled"])

        login_response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "owner@example.com", "password": "temporary-password"}),
            content_type="application/json",
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertFalse(login_response.json()["authenticated"])
        self.assertTrue(login_response.json()["totpRequired"])

        verify_response = self.client.post(
            "/api/v1/auth/totp/verify/",
            data=json.dumps({"code": _totp_code(owner.totp_secret)}),
            content_type="application/json",
        )

        self.assertEqual(verify_response.status_code, 200)
        self.assertTrue(verify_response.json()["authenticated"])


@override_settings(ROOT_URLCONF="chatballs_backend.urls_admin")
class DjangoAdminTests(TestCase):
    def test_bootstrapped_owner_can_access_django_admin(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        client = Client()
        self.assertTrue(client.login(username="owner@example.com", password="temporary-password"))

        response = client.get("/admin/")

        self.assertEqual(response.status_code, 200)


class EmployeeEndpointTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def test_owner_cannot_create_operator_with_temporary_password(self) -> None:
        response = self.client.post(
            "/api/v1/employees/operators/",
            data=json.dumps(
                {
                    "email": "operator@example.com",
                    "fullName": "Operator",
                    "positionTitle": "Оператор продаж",
                    "temporaryPassword": "operator-password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(HumanUser.objects.filter(email="operator@example.com").exists())

    def test_operator_cannot_create_operator(self) -> None:
        operator = HumanUser.objects.create_user(email="operator@example.com", password="operator-password")
        OrganizationMembership.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
        )
        self.client.logout()
        self.client.login(username="operator@example.com", password="operator-password")

        response = self.client.post(
            "/api/v1/employees/operators/",
            data=json.dumps(
                {
                    "email": "another@example.com",
                    "temporaryPassword": "operator-password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="identity.employee_privileged_action_denied"
            ).exists()
        )

    def test_owner_blocks_operator(self) -> None:
        operator = HumanUser.objects.create_user(email="operator@example.com", password="operator-password")
        OrganizationMembership.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
        )

        response = self.client.post(f"/api/v1/employees/{operator.id}/block/")

        self.assertEqual(response.status_code, 200)
        operator.refresh_from_db()
        self.assertTrue(operator.is_active)
        self.assertTrue(operator.memberships.get().is_blocked)
        self.assertTrue(AuditEvent.objects.filter(action="identity.employee_blocked").exists())

    def test_owner_updates_operator_card_fields(self) -> None:
        operator = HumanUser.objects.get(email="staff.member@example.org")

        response = self.client.post(
            f"/api/v1/employees/{operator.id}/update/",
            data=json.dumps(
                {
                    "fullName": "Анна Котова",
                    "email": "anna.kotova@example.com",
                    "phone": "+7 916 245 14 03",
                    "positionTitle": "Оператор продаж",
                    "role": EmployeeRole.EMPLOYEE,
                    "totpEnabled": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        operator.refresh_from_db()
        operator.memberships.get().refresh_from_db()
        self.assertEqual(operator.email, "anna.kotova@example.com")
        self.assertEqual(operator.memberships.get().phone, "+7 916 245 14 03")
        self.assertFalse(operator.totp_enabled)

    def test_owner_cannot_reset_operator_global_password(self) -> None:
        operator = HumanUser.objects.get(email="staff.member@example.org")
        password_hash = operator.password

        response = self.client.post(f"/api/v1/employees/{operator.id}/reset-password/")

        self.assertEqual(response.status_code, 403)
        operator.refresh_from_db()
        self.assertEqual(operator.password, password_hash)
        self.assertFalse(operator.must_change_password)

    def test_owner_unblocks_operator(self) -> None:
        operator = HumanUser.objects.get(email="staff.member@example.org")
        operator.memberships.get().block()

        response = self.client.post(f"/api/v1/employees/{operator.id}/unblock/")

        self.assertEqual(response.status_code, 200)
        operator.refresh_from_db()
        operator.memberships.get().refresh_from_db()
        self.assertTrue(operator.is_active)
        self.assertFalse(operator.memberships.get().is_blocked)


class CompanyEndpointTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def test_owner_reads_groups_and_products(self) -> None:
        groups_response = self.client.get("/api/v1/company/groups/")
        products_response = self.client.get("/api/v1/company/products/")

        self.assertEqual(groups_response.status_code, 200)
        self.assertEqual(products_response.status_code, 200)
        self.assertEqual(
            set(group["name"] for group in groups_response.json()["items"]),
            {"Операторы", "Поддержка"},
        )
        self.assertEqual(
            set(product["code"] for product in products_response.json()["items"]),
            {"site", "app"},
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
        self.assertTrue(AuditEvent.objects.filter(action="products.product_created").exists())
        self.assertTrue(AuditEvent.objects.filter(action="products.product_disabled").exists())

    def test_operator_cannot_create_product(self) -> None:
        operator = HumanUser.objects.create_user(email="operator@example.com", password="operator-password")
        OrganizationMembership.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
        )
        self.client.logout()
        self.client.login(username="operator@example.com", password="operator-password")

        response = self.client.post(
            "/api/v1/company/products/create/",
            data=json.dumps({"code": "academy", "name": "Academy"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)


class TotpSecretEncryptionTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")

    def test_totp_secret_is_encrypted_at_rest_and_decrypted_on_load(self) -> None:
        from django.db import connection

        from chatballs.identity.crypto import decrypt_secret

        owner = HumanUser.objects.get(email="owner@example.com")
        owner.totp_secret = "JBSWY3DPEHPK3PXP"
        owner.save(update_fields=["totp_secret"])

        with connection.cursor() as cursor:
            cursor.execute("SELECT totp_secret FROM identity_humanuser WHERE id = %s", [owner.id])
            stored = cursor.fetchone()[0]

        self.assertNotEqual(stored, "JBSWY3DPEHPK3PXP")
        self.assertEqual(decrypt_secret(stored), "JBSWY3DPEHPK3PXP")

        owner.refresh_from_db()
        self.assertEqual(owner.totp_secret, "JBSWY3DPEHPK3PXP")


@override_settings(CACHES=_LOCMEM_CACHE)
class ThrottlingTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.client = Client()

    def _login(self):
        return self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"email": "owner@example.com", "password": "wrong"}),
            content_type="application/json",
        )

    def test_login_endpoint_is_rate_limited(self) -> None:
        # DRF биндит THROTTLE_RATES на импорте, поэтому ставим лимит напрямую.
        with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "1/min"}):
            first = self._login()
            second = self._login()

        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)


class EmployeeModelInvariantTests(TestCase):
    """ADR-HUB-0027 / SPEC-HUB-0016 §5,§7 — инварианты модели сотрудника после
    миграции этапа 1: роли OWNER/ADMIN/EMPLOYEE, обязательная должность,
    размещение владельца на уровне компании и ровно один владелец на организацию."""

    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")

    def test_bootstrap_owner_has_owner_role_and_title(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        self.assertEqual(owner.memberships.get().role, EmployeeRole.OWNER)
        self.assertTrue(owner.memberships.get().position_title)

    def test_bootstrapped_operator_is_employee_in_operators_group(self) -> None:
        operator = HumanUser.objects.get(email="staff.member@example.org")
        self.assertEqual(operator.memberships.get().role, EmployeeRole.EMPLOYEE)
        self.assertEqual(
            [link.group.name for link in operator.memberships.get().group_links.all()],
            ["Операторы"],
        )
        self.assertTrue(operator.memberships.get().position_title)

    def test_second_owner_is_rejected(self) -> None:
        from django.db import IntegrityError, transaction

        second = HumanUser.objects.create_user(email="owner2@example.com", password="temporary-password")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrganizationMembership.objects.create(
                    user=second,
                    organization=self.organization,
                    role=EmployeeRole.OWNER,
                    position_title="Второй владелец",
                )

    def test_create_employee_requires_position_title(self) -> None:
        client = APIClient()
        client.login(username="owner@example.com", password="temporary-password")
        response = client.post(
            "/api/v1/employees/operators/",
            data=json.dumps(
                {
                    "email": "no-title@example.com",
                    "fullName": "No Title",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(HumanUser.objects.filter(email="no-title@example.com").exists())


class EmployeeGovernanceTests(TestCase):
    """ADR-HUB-0027 этап 2 / SPEC-HUB-0016 §8,§12: административная иерархия
    OWNER/ADMIN/EMPLOYEE, target-aware управление и передача владения."""

    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")

    def _make(self, email: str, role: str) -> HumanUser:
        user = HumanUser.objects.create_user(email=email, password="member-password-123")
        OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=role,
            position_title="Позиция",
        )
        return user

    def _client(self, email: str, password: str = "member-password-123") -> APIClient:
        client = APIClient()
        client.login(username=email, password=password)
        return client

    def _create(self, client: APIClient, email: str, role: str) -> "object":
        return client.post(
            "/api/v1/employees/operators/",
            data=json.dumps(
                {
                    "email": email,
                    "fullName": "New Member",
                    "positionTitle": "Позиция",
                    "role": role,
                }
            ),
            content_type="application/json",
        )

    # --- создание и назначение ролей ---

    def test_owner_creates_admin(self) -> None:
        client = self._client("owner@example.com", "temporary-password")
        response = self._create(client, "admin@example.com", EmployeeRole.ADMIN)
        self.assertEqual(response.status_code, 201)
        profile = HumanUser.objects.get(email="admin@example.com").memberships.get()
        self.assertEqual(profile.role, EmployeeRole.ADMIN)
        self.assertTrue(AuditEvent.objects.filter(action="identity.employee_created").exists())

    def test_admin_creates_admin(self) -> None:
        # SPEC-HUB-0031 §3: ADMIN идентичен OWNER и может создавать админов.
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._create(self._client("admin@example.com"), "admin2@example.com", EmployeeRole.ADMIN)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            HumanUser.objects.get(email="admin2@example.com").memberships.get().role,
            EmployeeRole.ADMIN,
        )

    def test_admin_creates_employee(self) -> None:
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._create(self._client("admin@example.com"), "emp@example.com", EmployeeRole.EMPLOYEE)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            HumanUser.objects.get(email="emp@example.com").memberships.get().role,
            EmployeeRole.EMPLOYEE,
        )

    def test_create_owner_via_flow_is_rejected(self) -> None:
        client = self._client("owner@example.com", "temporary-password")
        response = self._create(client, "owner2@example.com", EmployeeRole.OWNER)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(HumanUser.objects.filter(email="owner2@example.com").exists())

    # --- target-aware управление ---

    def test_admin_can_block_employee(self) -> None:
        emp = self._make("emp@example.com", EmployeeRole.EMPLOYEE)
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._client("admin@example.com").post(f"/api/v1/employees/{emp.id}/block/")
        self.assertEqual(response.status_code, 200)
        emp.refresh_from_db()
        self.assertTrue(emp.is_active)
        self.assertTrue(emp.memberships.get().is_blocked)

    def test_admin_blocks_another_admin(self) -> None:
        # SPEC-HUB-0031 §3: админы управляют друг другом; защищён только владелец.
        other = self._make("admin2@example.com", EmployeeRole.ADMIN)
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._client("admin@example.com").post(f"/api/v1/employees/{other.id}/block/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(other.memberships.get().is_blocked)

    def test_admin_cannot_block_owner(self) -> None:
        owner = HumanUser.objects.get(email="owner@example.com")
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._client("admin@example.com").post(f"/api/v1/employees/{owner.id}/block/")
        self.assertEqual(response.status_code, 403)
        owner.refresh_from_db()
        self.assertTrue(owner.is_active)

    def test_admin_updates_another_admin(self) -> None:
        other = self._make("admin2@example.com", EmployeeRole.ADMIN)
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._client("admin@example.com").post(
            f"/api/v1/employees/{other.id}/update/",
            data=json.dumps({"fullName": "Renamed", "email": "admin2@example.com", "positionTitle": "X"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        other.refresh_from_db()
        self.assertEqual(other.full_name, "Renamed")

    def test_admin_promotes_employee_to_admin(self) -> None:
        emp = self._make("emp@example.com", EmployeeRole.EMPLOYEE)
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._client("admin@example.com").post(
            f"/api/v1/employees/{emp.id}/update/",
            data=json.dumps(
                {"fullName": "Emp", "email": "emp@example.com", "positionTitle": "X", "role": EmployeeRole.ADMIN}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        emp.memberships.get().refresh_from_db()
        self.assertEqual(emp.memberships.get().role, EmployeeRole.ADMIN)

    def test_owner_promotes_employee_to_admin(self) -> None:
        emp = self._make("emp@example.com", EmployeeRole.EMPLOYEE)
        response = self._client("owner@example.com", "temporary-password").post(
            f"/api/v1/employees/{emp.id}/update/",
            data=json.dumps(
                {"fullName": "Emp", "email": "emp@example.com", "positionTitle": "X", "role": EmployeeRole.ADMIN}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        emp.memberships.get().refresh_from_db()
        self.assertEqual(emp.memberships.get().role, EmployeeRole.ADMIN)
        self.assertTrue(AuditEvent.objects.filter(action="identity.employee_role_changed").exists())

    def test_employee_cannot_manage(self) -> None:
        emp = self._make("emp@example.com", EmployeeRole.EMPLOYEE)
        other = self._make("emp2@example.com", EmployeeRole.EMPLOYEE)
        response = self._client("emp@example.com").post(f"/api/v1/employees/{other.id}/block/")
        self.assertEqual(response.status_code, 403)
        emp.refresh_from_db()

    def test_cross_org_target_is_not_found(self) -> None:
        other_org = Organization.objects.create(name="Other", slug="other")
        outsider = HumanUser.objects.create_user(email="out@other.tech", password="member-password-123")
        OrganizationMembership.objects.create(
            user=outsider, organization=other_org, role=EmployeeRole.EMPLOYEE, position_title="X"
        )
        response = self._client("owner@example.com", "temporary-password").post(
            f"/api/v1/employees/{outsider.id}/block/"
        )
        self.assertEqual(response.status_code, 404)

    # --- передача владения ---

    def test_owner_transfers_ownership_atomically(self) -> None:
        target = self._make("heir@example.com", EmployeeRole.EMPLOYEE)
        owner = HumanUser.objects.get(email="owner@example.com")
        response = self._client("owner@example.com", "temporary-password").post(
            f"/api/v1/employees/{target.id}/transfer-ownership/",
            data=json.dumps({"previousOwnerRole": EmployeeRole.ADMIN}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        target.memberships.get().refresh_from_db()
        owner.memberships.get().refresh_from_db()
        self.assertEqual(target.memberships.get().role, EmployeeRole.OWNER)
        self.assertEqual(owner.memberships.get().role, EmployeeRole.ADMIN)
        self.assertEqual(
            OrganizationMembership.objects.filter(organization=self.organization, role=EmployeeRole.OWNER).count(),
            1,
        )
        self.assertTrue(AuditEvent.objects.filter(action="identity.ownership_transferred").exists())

    def test_admin_cannot_transfer_ownership(self) -> None:
        target = self._make("heir@example.com", EmployeeRole.EMPLOYEE)
        self._make("admin@example.com", EmployeeRole.ADMIN)
        response = self._client("admin@example.com").post(
            f"/api/v1/employees/{target.id}/transfer-ownership/",
            data=json.dumps({"previousOwnerRole": EmployeeRole.EMPLOYEE}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            OrganizationMembership.objects.filter(organization=self.organization, role=EmployeeRole.OWNER).count(),
            1,
        )

    # --- обычные capability ADMIN ---

    def test_admin_has_normal_capabilities(self) -> None:
        self._make("admin@example.com", EmployeeRole.ADMIN)
        client = self._client("admin@example.com")
        audit = client.get("/api/v1/company/administration/audit/")
        self.assertEqual(audit.status_code, 200)
        product = client.post(
            "/api/v1/company/products/create/",
            data=json.dumps({"code": "academy", "name": "Academy"}),
            content_type="application/json",
        )
        self.assertEqual(product.status_code, 201)

    def test_employee_denied_audit(self) -> None:
        self._make("emp@example.com", EmployeeRole.EMPLOYEE)
        response = self._client("emp@example.com").get("/api/v1/company/administration/audit/")
        self.assertEqual(response.status_code, 403)

    def test_payload_permissions_reflect_actor(self) -> None:
        self._make("emp@example.com", EmployeeRole.EMPLOYEE)
        self._make("admin@example.com", EmployeeRole.ADMIN)
        items = self._client("admin@example.com").get("/api/v1/employees/").json()["items"]
        by_email = {item["email"]: item for item in items}
        # ADMIN идентичен OWNER: управляет всеми, кроме блокировки/удаления владельца.
        self.assertTrue(by_email["emp@example.com"]["permissions"]["canBlock"])
        self.assertTrue(by_email["emp@example.com"]["permissions"]["canChangeRole"])
        self.assertFalse(by_email["owner@example.com"]["permissions"]["canBlock"])
        self.assertTrue(by_email["owner@example.com"]["permissions"]["canUpdateProfile"])
