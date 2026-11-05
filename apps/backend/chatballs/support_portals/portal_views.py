"""HTTP adapters for shared portal commands and reads."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.support_portals import portal_commands as commands
from chatballs.support_portals import portal_queries as queries
from chatballs.support_portals.api import validation_response
from chatballs.support_portals.models import SupportPortal
from chatballs.support_portals.selectors import portal_for_context


class PortalBaseView(APIView):
    permission_classes = [HasCapability]
    required_capability = "support.view"
    required_capabilities = {"GET": "support.view", **dict.fromkeys(
        ("POST", "PATCH", "PUT", "DELETE"), "support.operate")}

    def portal(self, request, portal_id):
        try:
            return portal_for_context(request.tenant_context, portal_id)
        except SupportPortal.DoesNotExist:
            return None

    def result(self, http_request, operation, *args, status=200, **kwargs):
        try:
            payload = operation(http_request.tenant_context, *args, **kwargs)
        except SupportPortal.DoesNotExist:
            return Response({"detail": t("portals.not_found")}, status=404)
        except ValidationError as error:
            return validation_response(error)
        return Response(payload, status=status)


class PortalListView(PortalBaseView):
    def get(self, request):
        return self.result(request, queries.listing, request.query_params)

    def post(self, request):
        return self.result(request, commands.create, request.data, request=request, status=201)


class PortalDetailView(PortalBaseView):
    def get(self, request, portal_id):
        return self.result(request, queries.detail, portal_id)

    def patch(self, request, portal_id):
        return self.result(request, commands.update, portal_id, request.data)


class PortalStatusView(PortalBaseView):
    def post(self, request, portal_id):
        return self.result(request, commands.status, portal_id, request.data, request=request)


class PortalWidgetOptionsView(PortalBaseView):
    def get(self, request, portal_id):
        return self.result(request, queries.widgets, portal_id)


class PortalDomainView(PortalBaseView):
    def put(self, request, portal_id):
        return self.result(request, commands.domain, portal_id, request.data)


class PortalDomainVerifyView(PortalBaseView):
    def post(self, request, portal_id):
        return self.result(request, commands.verify_domain, portal_id)
