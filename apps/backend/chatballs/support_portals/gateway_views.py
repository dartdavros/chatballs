from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.identity.instance_settings import accepted_hosts
from chatballs.support_portals.addressing import normalize_domain
from chatballs.tenancy.ingress import support_portal_route


class HelpDomainAuthorizationView(APIView):
    """Caddy on-demand TLS authorization.

    Шлюз спрашивает разрешение перед выпуском сертификата на каждый новый хост.
    Разрешены два вида адресов, и оба человек задал сам в интерфейсе:

    - адрес самой установки (мастер первого запуска запомнил его, владелец
      меняет в «Настройках») — без этого коробка навсегда оставалась бы на
      http: свой домен ей выписать было нечем;
    - домены опубликованных порталов помощи.

    Всё остальное — 404, иначе любой указавший на нас домен заставлял бы
    установку ходить в ACME.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        domain = normalize_domain(str(request.query_params.get("domain", "")))
        if not domain:
            return Response(status=404)
        if domain in {normalize_domain(item) for item in accepted_hosts()}:
            return Response(status=204)
        if support_portal_route(domain) is None:
            return Response(status=404)
        return Response(status=204)
