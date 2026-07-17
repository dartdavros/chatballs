from django.test import TestCase, override_settings


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
class LocalCorsMiddlewareTests(TestCase):
    def test_allowed_origin_receives_cors_headers(self) -> None:
        response = self.client.get("/api/v1/auth/session/", HTTP_ORIGIN="http://localhost:5173")

        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")

    def test_unknown_origin_gets_no_cors_headers(self) -> None:
        response = self.client.get("/api/v1/auth/session/", HTTP_ORIGIN="https://evil.example")

        self.assertFalse(response.has_header("Access-Control-Allow-Origin"))

    def test_preflight_from_allowed_origin_short_circuits(self) -> None:
        response = self.client.options("/api/v1/auth/session/", HTTP_ORIGIN="http://localhost:5173")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:5173")


class ContentSecurityPolicyMiddlewareTests(TestCase):
    @override_settings(CUS_CONTENT_SECURITY_POLICY="default-src 'none'")
    def test_surface_policy_is_applied(self) -> None:
        response = self.client.get("/api/v1/health/live/")

        self.assertEqual(response["Content-Security-Policy"], "default-src 'none'")

    @override_settings(CUS_CONTENT_SECURITY_POLICY="")
    def test_empty_policy_does_not_add_header(self) -> None:
        response = self.client.get("/api/v1/health/live/")

        self.assertFalse(response.has_header("Content-Security-Policy"))
