from importlib import import_module

from django.test import SimpleTestCase, override_settings


class RuntimeSurfaceRouteTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF="hub_backend.urls_app")
    def test_app_exposes_tenant_api_but_not_admin(self) -> None:
        self.assertEqual(self.client.get("/api/v1/health/live/").status_code, 200)
        self.assertNotEqual(self.client.get("/api/v1/auth/session/").status_code, 404)
        self.assertEqual(self.client.get("/admin/login/").status_code, 404)

    @override_settings(ROOT_URLCONF="hub_backend.urls_platform")
    def test_platform_exposes_only_platform_health(self) -> None:
        self.assertEqual(self.client.get("/api/v1/health/live/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/session/").status_code, 404)
        self.assertEqual(self.client.get("/chat-widget.js").status_code, 404)
        self.assertEqual(self.client.get("/admin/login/").status_code, 404)

    @override_settings(ROOT_URLCONF="hub_backend.urls_admin")
    def test_admin_exposes_only_django_admin(self) -> None:
        self.assertEqual(self.client.get("/admin/login/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/health/live/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/auth/session/").status_code, 404)


class RuntimeSurfaceSettingsTests(SimpleTestCase):
    def test_cookie_names_are_isolated_and_host_only(self) -> None:
        surfaces = [
            import_module("hub_backend.settings_app"),
            import_module("hub_backend.settings_platform"),
            import_module("hub_backend.settings_admin"),
        ]

        self.assertEqual(len({surface.SESSION_COOKIE_NAME for surface in surfaces}), 3)
        self.assertEqual(len({surface.CSRF_COOKIE_NAME for surface in surfaces}), 3)
        self.assertTrue(all(surface.SESSION_COOKIE_DOMAIN is None for surface in surfaces))
        self.assertTrue(all(surface.CSRF_COOKIE_DOMAIN is None for surface in surfaces))

    def test_admin_hosts_are_loopback_only(self) -> None:
        admin_settings = import_module("hub_backend.settings_admin")

        self.assertEqual(admin_settings.ALLOWED_HOSTS, ["127.0.0.1", "localhost"])
