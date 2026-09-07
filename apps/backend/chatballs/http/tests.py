from django.conf import settings
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
    @override_settings(CHATBALLS_CONTENT_SECURITY_POLICY="default-src 'none'")
    def test_surface_policy_is_applied(self) -> None:
        response = self.client.get("/api/v1/health/live/")

        self.assertEqual(response["Content-Security-Policy"], "default-src 'none'")

    @override_settings(CHATBALLS_CONTENT_SECURITY_POLICY="")
    def test_empty_policy_does_not_add_header(self) -> None:
        response = self.client.get("/api/v1/health/live/")

        self.assertFalse(response.has_header("Content-Security-Policy"))


class TlsAwareCookieMiddlewareTests(TestCase):
    """Коробку сначала открывают по http, а TLS появляется позже (см. middleware)."""

    def test_plain_http_gets_usable_cookies_without_secure(self) -> None:
        # Без этого мастер первого запуска не смог бы завести владельца:
        # Secure-cookie по http браузер не сохраняет.
        response = self.client.get("/api/v1/auth/session/")

        cookie = response.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertIsNotNone(cookie)
        self.assertFalse(cookie["secure"])
        self.assertNotIn(settings.CHATBALLS_TLS_COOKIE_NAMES[settings.CSRF_COOKIE_NAME], response.cookies)

    def test_https_request_gets_host_prefixed_secure_cookies(self) -> None:
        response = self.client.get("/api/v1/auth/session/", secure=True)

        hardened = response.cookies.get(settings.CHATBALLS_TLS_COOKIE_NAMES[settings.CSRF_COOKIE_NAME])
        self.assertIsNotNone(hardened)
        self.assertTrue(hardened["secure"])
        self.assertEqual(hardened["path"], "/")
        self.assertEqual(hardened["domain"], "")
        self.assertNotIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_https_request_reads_back_host_prefixed_cookie(self) -> None:
        first = self.client.get("/api/v1/auth/session/", secure=True)
        token = first.cookies[settings.CHATBALLS_TLS_COOKIE_NAMES[settings.CSRF_COOKIE_NAME]].value
        self.client.cookies.clear()
        self.client.cookies[settings.CHATBALLS_TLS_COOKIE_NAMES[settings.CSRF_COOKIE_NAME]] = token

        response = self.client.get("/api/v1/auth/session/", secure=True)

        self.assertEqual(response.status_code, 200)

    def test_plain_http_is_not_redirected_to_https(self) -> None:
        # Установка без домена обязана отвечать по http, а не уводить браузер
        # на несуществующий https (иначе редирект залипает в кеше).
        response = self.client.get("/api/v1/health/live/")

        self.assertEqual(response.status_code, 200)
