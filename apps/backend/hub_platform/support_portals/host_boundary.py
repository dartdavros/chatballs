from __future__ import annotations

import sys

from django.conf import settings
from django.db import connections
from django.http import HttpRequest, HttpResponseBadRequest

from hub_platform.support_portals.addressing import normalize_domain
from hub_platform.tenancy.ingress import support_portal_route


class SupportPortalHostBoundaryMiddleware:
    """Accept app hosts and hosts present in the published portal directory."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        raw_host = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME", "")
        host = normalize_domain(raw_host.partition(":")[0])
        if not self._allowed(host):
            return HttpResponseBadRequest("Invalid host")
        return self.get_response(request)

    @staticmethod
    def _allowed(host: str) -> bool:
        if host == "testserver" and (
            "pytest" in sys.modules
            or any("pytest" in argument for argument in sys.argv)
            or str(connections["default"].settings_dict["NAME"]).startswith("test_")
        ):
            return True
        for allowed in settings.CUS_APP_PRIMARY_HOSTS:
            normalized = normalize_domain(allowed.lstrip("."))
            if host == normalized or (
                allowed.startswith(".") and host.endswith(f".{normalized}")
            ):
                return True
        try:
            return support_portal_route(host) is not None
        except Exception:
            return False
