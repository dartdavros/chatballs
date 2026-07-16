from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from hub_platform.subscriptions.errors import (
    EntitlementRequired,
    PolicyUnavailable,
    QuotaExceeded,
    SubscriptionDomainError,
    SubscriptionInactive,
    UsageConflict,
)


def _flatten(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return "; ".join(_flatten(value) for value in data.values())
    if isinstance(data, (list, tuple)):
        return "; ".join(_flatten(item) for item in data)
    return str(data)


def _domain_error_response(exc: SubscriptionDomainError):
    """Map subscription-domain errors to the SPA contract (SPEC-HUB-0022 §13).

    EntitlementRequired -> 403; QuotaExceeded HARD/period -> 409,
    RATE/CONCURRENT -> 429 (with Retry-After for RATE); PolicyUnavailable /
    SubscriptionInactive -> 503; UsageConflict -> 409. Other domain errors -> 409.
    """
    if isinstance(exc, EntitlementRequired):
        return Response(
            {"detail": str(exc), "code": exc.code, "entitlement": exc.entitlement},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, QuotaExceeded):
        is_rate_like = exc.mode in {"RATE", "CONCURRENT"}
        http_status = (
            status.HTTP_429_TOO_MANY_REQUESTS if is_rate_like else status.HTTP_409_CONFLICT
        )
        response = Response(
            {
                "detail": str(exc),
                "code": exc.code,
                "resource": exc.resource,
                "limit": exc.limit,
                "used": exc.used,
                "requested": exc.requested,
            },
            status=http_status,
        )
        if exc.mode == "RATE":
            # Advisory only: the client may retry once the window elides.
            response["Retry-After"] = "60"
        return response
    if isinstance(exc, PolicyUnavailable | SubscriptionInactive):
        return Response({"detail": str(exc), "code": exc.code}, status=503)
    if isinstance(exc, UsageConflict):
        return Response({"detail": str(exc), "code": exc.code}, status=status.HTTP_409_CONFLICT)
    return Response({"detail": str(exc), "code": exc.code}, status=status.HTTP_409_CONFLICT)


def api_exception_handler(exc: Exception, context: dict[str, Any]):
    """Normalize every DRF error body to the SPA contract: {"detail": "<text>"}.

    Subscription-domain exceptions are mapped to explicit HTTP statuses before DRF
    would otherwise render them as 500 (they are plain Exceptions, not APIException).
    """
    if isinstance(exc, SubscriptionDomainError):
        return _domain_error_response(exc)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if (
        isinstance(data, dict)
        and list(data.keys()) == ["detail"]
        and isinstance(data["detail"], str)
    ):
        return response
    response.data = {"detail": _flatten(data)}
    return response
