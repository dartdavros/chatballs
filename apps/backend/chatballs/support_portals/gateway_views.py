from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.support_portals.addressing import normalize_domain
from chatballs.tenancy.ingress import support_portal_route


class HelpDomainAuthorizationView(APIView):
    """Caddy on-demand TLS authorization for published portal hosts."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        domain = normalize_domain(str(request.query_params.get("domain", "")))
        if not domain or support_portal_route(domain) is None:
            return Response(status=404)
        return Response(status=204)
