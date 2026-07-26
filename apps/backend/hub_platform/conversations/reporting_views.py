from rest_framework.request import Request
from rest_framework.response import Response

from hub_platform.conversations.clients import client_detail, clients_overview
from hub_platform.conversations.command import command_center_overview
from hub_platform.conversations.models import Contact
from hub_platform.conversations.stats import sales_overview_stats
from hub_platform.conversations.view_base import ConversationViewBase
from hub_platform.identity.policy import accessible_department_ids


class ConversationStatsView(ConversationViewBase):
    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        department_ids = accessible_department_ids(
            request.tenant_context.membership, self.required_capability
        )
        return Response(
            sales_overview_stats(request.tenant_context, period, department_ids)
        )


class CommandOverviewView(ConversationViewBase):
    required_capability = "company.view"
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        return Response(command_center_overview(request.tenant_context, period))


class ClientsView(ConversationViewBase):
    required_capability = "customers.view"

    def get(self, request: Request) -> Response:
        department_ids = accessible_department_ids(
            request.tenant_context.membership, self.required_capability
        )
        return Response(
            {"items": clients_overview(self._org(request).id, department_ids)}
        )


class ClientDetailView(ConversationViewBase):
    required_capability = "customers.view"

    def get(self, request: Request, contact_id: int) -> Response:
        try:
            department_ids = accessible_department_ids(
                request.tenant_context.membership, self.required_capability
            )
            return Response(
                {
                    "client": client_detail(
                        self._org(request).id, contact_id, department_ids
                    )
                }
            )
        except Contact.DoesNotExist:
            return Response({"detail": "Клиент не найден"}, status=404)
