from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class LocalCorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        is_allowed_preflight = (
            request.method == "OPTIONS"
            and request.headers.get("Origin") in settings.CORS_ALLOWED_ORIGINS
        )
        if is_allowed_preflight:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        origin = request.headers.get("Origin")
        if origin in settings.CORS_ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Content-Type, X-Correlation-Id, X-CSRFToken"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Vary"] = "Origin"
        return response


class ContentSecurityPolicyMiddleware:
    """Apply the CSP selected by the current runtime surface."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        policy = settings.CUS_CONTENT_SECURITY_POLICY
        if policy and not response.has_header("Content-Security-Policy"):
            response["Content-Security-Policy"] = policy
        return response
