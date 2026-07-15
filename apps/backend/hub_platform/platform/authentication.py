from __future__ import annotations

from rest_framework.authentication import BaseAuthentication

from hub_platform.platform.models import PlatformOperator, PlatformToken
from hub_platform.platform.tokens import authenticate_token


class PlatformTokenAuthentication(BaseAuthentication):
    """Machine-to-machine auth via `Authorization: Token <opaque>`.

    The platform surface is non-browser (ADR-HUB-0031 §4): there is no CORS and
    session cookies are not used. On success, request.platform_operator and the
    authenticating PlatformToken are attached for capability checks and audit.
    """

    keyword = "Token"

    def authenticate(self, request):  # type: ignore[override]
        header = request.headers.get("Authorization", "")
        if not header.startswith(f"{self.keyword} "):
            return None
        raw_token = header[len(self.keyword) + 1 :].strip()
        token = authenticate_token(raw_token)
        if token is None:
            return None
        return (token.operator, token)

    def authenticate_header(self, request):  # type: ignore[override]
        return self.keyword

    def get_operator(self, request) -> PlatformOperator | None:
        """Helper for views needing the principal even when DRF has attached it
        as request.user (here we keep it explicit on the request object)."""
        return getattr(request, "platform_operator", None)


# DRF attaches the returned user/principal as request.user. The view layer reads
# request.user (a PlatformOperator) and the token via request.auth.
def get_platform_token(request) -> PlatformToken | None:
    return getattr(request, "auth", None)
