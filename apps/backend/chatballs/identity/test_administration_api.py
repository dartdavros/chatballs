from __future__ import annotations

from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from chatballs.identity.audit import record_audit_event
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient


class AdministrationApiTests(TestCase):
    def setUp(self) -> None:
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.organization = Organization.objects.create(
            name="Example",
            slug="administration",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        self.owner = HumanUser.objects.create_user(
            email="owner@administration.test",
            password="Password-123",
            full_name="Владелец",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=EmployeeRole.OWNER,
            position_title="Владелец",
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)

    @override_settings(CHATBALLS_DELIVERY_MODE="CLOUD")
    def test_session_exposes_delivery_mode_without_installation_inference(self) -> None:
        response = self.client.get("/api/v1/auth/session/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["deliveryMode"], "CLOUD")

    def test_settings_payload_contains_only_current_administration_fields(self) -> None:
        response = self.client.get("/api/v1/company/administration/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["organization"],
            {
                "name": "Example",
                "timezone": "Europe/Moscow",
                "currency": "RUB",
                "logoUrl": None,
                # Подпись «Сохранено …» у кнопки (кадр N1): пока правок не было — null.
                "updatedAt": None,
            },
        )
        self.assertIn("Europe/Moscow", response.json()["timezones"])
        self.assertGreater(len(response.json()["timezones"]), 300)
        self.assertNotIn("taxRegime", response.json()["organization"])

    def test_owner_updates_current_organization(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/",
            {
                "name": "Новая компания",
                "timezone": "Asia/Yekaterinburg",
                "currency": "rub",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.name, "Новая компания")
        self.assertEqual(self.organization.timezone, "Asia/Yekaterinburg")
        self.assertEqual(self.organization.currency, "RUB")

    def test_invalid_timezone_is_rejected(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/",
            {"timezone": "Nowhere/Invalid"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("timezone", response.json()["errors"])

    def test_only_ruble_currency_is_accepted(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/",
            {"currency": "USD"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("российский рубль", response.json()["errors"]["currency"])

    def test_logo_upload_download_and_delete(self) -> None:
        png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        uploaded = self.client.post(
            "/api/v1/company/administration/logo/",
            {"file": SimpleUploadedFile("logo.png", png, content_type="image/png")},
            format="multipart",
        )

        self.assertEqual(uploaded.status_code, 200)
        logo_url = uploaded.json()["organization"]["logoUrl"]
        self.assertTrue(logo_url.endswith("/company/administration/logo/"))
        session = self.client.get("/api/v1/auth/session/")
        self.assertEqual(
            session.json()["user"]["memberships"][0]["organizationLogoUrl"],
            logo_url,
        )

        downloaded = self.client.get("/api/v1/company/administration/logo/")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Content-Type"], "image/png")
        self.assertEqual(b"".join(downloaded.streaming_content), png)

        deleted = self.client.delete("/api/v1/company/administration/logo/")
        self.assertEqual(deleted.status_code, 200)
        self.assertIsNone(deleted.json()["organization"]["logoUrl"])

    def test_profile_avatar_upload_visible_to_colleagues(self) -> None:
        png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        uploaded = self.client.post(
            "/api/v1/auth/profile/avatar/",
            {"file": SimpleUploadedFile("me.png", png, content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 200)
        own_url = uploaded.json()["user"]["avatarUrl"]
        self.assertTrue(own_url.startswith("/api/v1/auth/profile/avatar/?v="))
        self.assertEqual(self.client.get("/api/v1/auth/profile/avatar/").status_code, 200)

        # Коллеги видят фото через тенантный эндпоинт; ссылка приходит в списке сотрудников.
        employees = self.client.get("/api/v1/employees/").json()["items"]
        colleague_url = employees[0]["avatarUrl"]
        self.assertIn(f"/employees/{self.owner.id}/avatar/", colleague_url)
        self.assertEqual(self.client.get(colleague_url.split("?")[0]).status_code, 200)

        removed = self.client.delete("/api/v1/auth/profile/avatar/")
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.json()["user"]["avatarUrl"])
        self.assertEqual(self.client.get("/api/v1/auth/profile/avatar/").status_code, 404)

    def test_group_color_is_stored_and_validated(self) -> None:
        created = self.client.post(
            "/api/v1/company/groups/", {"name": "Операторы", "color": "#2AA876"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["group"]["color"], "#2aa876")
        bad = self.client.post("/api/v1/company/groups/", {"name": "Плохая", "color": "red"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_non_image_logo_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/company/administration/logo/",
            {
                "file": SimpleUploadedFile(
                    "logo.svg",
                    b"<svg></svg>",
                    content_type="image/svg+xml",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("PNG, JPEG и WebP", response.json()["detail"])

    def test_audit_returns_readable_text_instead_of_internal_action_codes(self) -> None:
        record_audit_event(
            action="administration.organization_updated",
            actor=self.owner,
            organization=self.organization,
        )

        response = self.client.get("/api/v1/company/administration/audit/")

        self.assertEqual(response.status_code, 200)
        event = response.json()["items"][0]
        self.assertEqual(event["action"], "Изменены данные организации")
        self.assertNotIn("administration.", event["action"])


class InstanceAddressTests(TestCase):
    """Адрес установки правится в «Настройках», а не в переменных окружения."""

    def setUp(self) -> None:
        result = bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = result.organization
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def test_owner_sets_domain_and_scheme(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/instance/",
            {"publicHost": "crm.example.com", "publicScheme": "https"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["instance"]
        self.assertEqual(body["publicHost"], "crm.example.com")
        self.assertEqual(body["publicUrl"], "https://crm.example.com")

    def test_address_may_be_a_bare_ip(self) -> None:
        # Коробку часто так и оставляют: сервер по IP, без домена.
        response = self.client.patch(
            "/api/v1/company/administration/instance/",
            {"publicHost": "203.0.113.10", "publicScheme": "http"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["instance"]["publicUrl"], "http://203.0.113.10")

    def test_url_is_accepted_and_trimmed_to_host(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/instance/",
            {"publicHost": "https://crm.example.com/settings", "publicScheme": "https"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["instance"]["publicHost"], "crm.example.com")

    def test_garbage_is_rejected(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/instance/",
            {"publicHost": "не адрес!", "publicScheme": "ftp"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)


class InstanceEmailTests(TestCase):
    """Почта установки задаётся в «Настройках»: без неё некого приглашать."""

    def setUp(self) -> None:
        result = bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def patch(self, **email):
        return self.client.patch(
            "/api/v1/company/administration/instance/",
            {"publicHost": "crm.example.com", "publicScheme": "https", "email": email},
            format="json",
        )

    def test_smtp_is_saved_and_password_is_not_returned(self) -> None:
        response = self.patch(
            host="smtp.example.com",
            port=465,
            user="robot@example.com",
            password="s3cret",
            useTls=True,
            **{"from": "Chatballs <robot@example.com>"},
        )

        self.assertEqual(response.status_code, 200, response.content)
        email = response.json()["instance"]["email"]
        self.assertEqual(email["host"], "smtp.example.com")
        self.assertEqual(email["port"], 465)
        self.assertTrue(email["configured"])
        self.assertTrue(email["hasPassword"])
        self.assertNotIn("password", email)

    def test_empty_password_keeps_the_stored_one(self) -> None:
        self.patch(host="smtp.example.com", password="s3cret")

        response = self.patch(host="smtp.example.com", password="")

        self.assertTrue(response.json()["instance"]["email"]["hasPassword"])

    def test_check_without_smtp_explains_itself(self) -> None:
        response = self.client.post(
            "/api/v1/company/administration/instance/email-check/", {}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("сервер исходящей почты", response.json()["detail"])
