from __future__ import annotations

from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.subscriptions.default_subscription import ensure_default_subscription
from hub_platform.testing import TenantAPIClient


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
        ensure_default_subscription(self.organization, quantity=3)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)

    @override_settings(CUS_DELIVERY_MODE="CLOUD")
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

    @override_settings(CUS_DELIVERY_MODE="CLOUD")
    def test_cloud_exposes_real_subscription_summary(self) -> None:
        response = self.client.get("/api/v1/company/administration/subscription/")

        self.assertEqual(response.status_code, 200)
        subscription = response.json()["subscription"]
        self.assertEqual(subscription["planName"], "Стартап")
        self.assertEqual(subscription["aiAgentQuantity"], 3)
        self.assertEqual(subscription["monthlyChargeMinor"], 870_000)

    @override_settings(CUS_DELIVERY_MODE="SELF_HOSTED")
    def test_self_hosted_rejects_cloud_subscription_endpoint(self) -> None:
        response = self.client.get("/api/v1/company/administration/subscription/")

        self.assertEqual(response.status_code, 403)

    def test_audit_returns_product_text_instead_of_internal_action_codes(self) -> None:
        record_audit_event(
            action="products.product_created",
            actor=self.owner,
            organization=self.organization,
        )

        response = self.client.get("/api/v1/company/administration/audit/")

        self.assertEqual(response.status_code, 200)
        event = response.json()["items"][0]
        self.assertEqual(event["action"], "Добавлен продукт")
        self.assertNotIn("products.", event["action"])
