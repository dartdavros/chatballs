from rest_framework.request import Request
from rest_framework.response import Response

from hub_platform.conversations.clients import client_detail, clients_overview
from hub_platform.conversations.models import Contact
from hub_platform.conversations.stats import sales_overview_stats
from hub_platform.conversations.view_base import ConversationViewBase


class ConversationStatsView(ConversationViewBase):
    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        return Response(sales_overview_stats(request.tenant_context, period))


class ClientsView(ConversationViewBase):
    required_capability = "customers.view"

    def get(self, request: Request) -> Response:
        return Response({"items": clients_overview(self._org(request).id)})


class ClientDetailView(ConversationViewBase):
    required_capability = "customers.view"

    def get(self, request: Request, contact_id: int) -> Response:
        try:
            return Response({"client": client_detail(self._org(request).id, contact_id)})
        except Contact.DoesNotExist:
            return Response({"detail": "Клиент не найден"}, status=404)
