from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from chatballs.platform.models import PlatformToken
from chatballs.platform.testing import create_platform_operator


def _client(token: str | None) -> APIClient:
    client = APIClient()
    if token is not None:
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@override_settings(ROOT_URLCONF="chatballs_backend.urls_platform")
class PlatformAuthTests(TestCase):
    def setUp(self) -> None:
        self.operator, self.token = create_platform_operator()

    def test_valid_token_provisions_organization(self) -> None:
        client = _client(self.token)
        response = client.post(
            "/api/v1/organizations",
            data={
                "name": "Acme",
                "slug": "acme",
                "owner_email": "owner-acme@example.test",
                "timezone": "Europe/Moscow",
                "currency": "RUB",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-api-1",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn("organization", response.json())
        self.assertIn("publicId", response.json()["organization"])
        # Тарифный контур удалён (ADR-HUB-0042): ответ без ключа subscription.
        self.assertNotIn("subscription", response.json())

    def test_missing_token_is_unauthenticated(self) -> None:
        client = _client(None)
        response = client.post("/api/v1/organizations", data={}, HTTP_IDEMPOTENCY_KEY="x")
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_is_unauthenticated(self) -> None:
        client = _client("ctp_not_a_real_token")
        response = client.post("/api/v1/organizations", data={}, HTTP_IDEMPOTENCY_KEY="x")
        self.assertEqual(response.status_code, 401)

    def test_revoked_token_is_unauthenticated(self) -> None:
        from django.utils import timezone

        PlatformToken.objects.filter(operator=self.operator).update(revoked_at=timezone.now())
        client = _client(self.token)
        response = client.post("/api/v1/organizations", data={}, HTTP_IDEMPOTENCY_KEY="x")
        self.assertEqual(response.status_code, 401)


@override_settings(ROOT_URLCONF="chatballs_backend.urls_platform")
class PlatformCapabilityGateTests(TestCase):
    def test_token_without_capability_is_forbidden(self) -> None:
        operator, _token = create_platform_operator(capabilities=[])
        client = _client(_token)
        response = client.post(
            "/api/v1/organizations",
            data={
                "name": "Acme",
                "slug": "acme",
                "owner_email": "owner-acme@example.test",
                "timezone": "Europe/Moscow",
                "currency": "RUB",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-api-2",
        )
        self.assertEqual(response.status_code, 403, response.content)
