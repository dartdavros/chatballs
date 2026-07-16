from __future__ import annotations

from django.test import RequestFactory, TestCase

from hub_platform.api.exceptions import api_exception_handler
from hub_platform.subscriptions.errors import (
    EntitlementRequired,
    PolicyUnavailable,
    QuotaExceeded,
    UsageConflict,
)


def _response(exc):
    factory = RequestFactory()
    request = factory.post("/", data={}, content_type="application/json")
    response = api_exception_handler(exc, {"request": request})
    return response


class EnforcementMappingTests(TestCase):
    def test_entitlement_required_maps_to_403(self) -> None:
        response = _response(EntitlementRequired("p2p_calls"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["entitlement"], "p2p_calls")

    def test_hard_quota_exceeded_maps_to_409(self) -> None:
        response = _response(
            QuotaExceeded(
                resource="products", limit=1, used=1, requested=1, mode="HARD"
            )
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["resource"], "products")

    def test_concurrent_quota_exceeded_maps_to_429(self) -> None:
        response = _response(
            QuotaExceeded(
                resource="concurrent_p2p_calls",
                limit=2,
                used=2,
                requested=1,
                mode="CONCURRENT",
            )
        )
        self.assertEqual(response.status_code, 429)

    def test_rate_quota_exceeded_maps_to_429_with_retry_after(self) -> None:
        response = _response(
            QuotaExceeded(resource="crm_api_requests", limit=60, used=60, requested=1, mode="RATE")
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "60")

    def test_policy_unavailable_maps_to_503(self) -> None:
        response = _response(PolicyUnavailable("no subscription"))
        self.assertEqual(response.status_code, 503)

    def test_usage_conflict_maps_to_409(self) -> None:
        response = _response(UsageConflict("negative"))
        self.assertEqual(response.status_code, 409)
