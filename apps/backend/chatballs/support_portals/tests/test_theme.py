from chatballs.support_portals.models import SupportPortal
from chatballs.support_portals.tests.base import SupportPortalTestCase


class SupportPortalThemeTests(SupportPortalTestCase):
    def test_new_portal_uses_default_theme(self) -> None:
        payload = self.create_portal().json()["portal"]

        self.assertEqual(payload["theme"], "classic")
        self.assertEqual(payload["themeScheme"], "LIGHT")
        self.assertEqual(payload["themeSettings"], {})

    def test_theme_is_saved_and_returned(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]

        response = self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {
                "theme": "Aurora-Dark",
                "themeScheme": "SYSTEM",
                "themeSettings": {"accent": "#1677ff"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()["portal"]
        self.assertEqual(payload["theme"], "aurora-dark")
        self.assertEqual(payload["themeScheme"], "SYSTEM")
        self.assertEqual(payload["themeSettings"], {"accent": "#1677ff"})

    def test_partial_update_keeps_theme(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {"theme": "aurora", "themeScheme": "DARK"},
            format="json",
        )

        response = self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {"name": "Другое имя"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["portal"]["theme"], "aurora")
        self.assertEqual(response.json()["portal"]["themeScheme"], "DARK")

    def test_invalid_theme_identifier_is_rejected(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]

        response = self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {"theme": "../etc/passwd"},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            SupportPortal.objects.get(id=portal_id).theme,
            "classic",
        )

    def test_invalid_scheme_and_settings_are_rejected(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]

        scheme = self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {"themeScheme": "NEON"},
            format="json",
        )
        settings_response = self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {"themeSettings": ["accent"]},
            format="json",
        )

        self.assertEqual(scheme.status_code, 400, scheme.content)
        self.assertIn("themeScheme", scheme.json()["errors"])
        self.assertEqual(settings_response.status_code, 400, settings_response.content)
        self.assertIn("themeSettings", settings_response.json()["errors"])

    def test_public_manifest_exposes_theme(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {"theme": "aurora", "themeScheme": "SYSTEM"},
            format="json",
        )
        published = self.client.post(
            f"/api/v1/support/portals/{portal_id}/status/",
            {"status": "PUBLISHED"},
            format="json",
        )
        self.assertEqual(published.status_code, 200, published.content)
        host = SupportPortal.objects.get(id=portal_id).hosted_domain
        self.client.logout()

        response = self.client.get("/api/v1/help/", HTTP_HOST=host)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["portal"]["theme"], "aurora")
        self.assertEqual(response.json()["portal"]["themeScheme"], "SYSTEM")
