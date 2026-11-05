"""HTTP boundary for shared agent card commands and reads."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai import agent_card_commands as commands
from chatballs.ai import agent_card_queries as queries
from chatballs.api.permissions import HasCapability
from chatballs.channels.models import Channel
from chatballs.channels.services import ChannelHasReferences, ConnectionAlreadyBound
from chatballs.i18n import t


class AgentCardView(APIView):
    permission_classes = [HasCapability]

    def handle_exception(self, error):
        if isinstance(error, Channel.DoesNotExist):
            return Response({"detail": t("ai.agent_not_found")}, status=404)
        if isinstance(error, ValidationError):
            messages = ([message for values in error.message_dict.values() for message in values]
                if hasattr(error, "message_dict") else error.messages)
            return Response({"detail": "; ".join(messages)}, status=400)
        if isinstance(error, ChannelHasReferences | ConnectionAlreadyBound):
            return Response(error.payload(), status=409)
        return super().handle_exception(error)

    @staticmethod
    def body(request):
        return request.data if isinstance(request.data, dict) else {}


class AgentDirectoryView(AgentCardView):
    required_capability = "ai.view"

    def get(self, request):
        return Response(queries.directory(request.tenant_context, request.query_params))


class AgentCardListView(AgentCardView):
    required_capabilities = {"GET": "ai.view", "POST": "ai.manage"}

    def get(self, request):
        return Response(queries.listing(request.tenant_context, request.query_params))

    def post(self, request):
        return Response(commands.create(request.tenant_context, self.body(request), request=request), status=201)


class AgentCardDetailView(AgentCardView):
    required_capabilities = {"GET": "ai.view", "PATCH": "ai.manage", "DELETE": "ai.manage"}

    def get(self, request, agent_id):
        return Response(queries.detail(request.tenant_context, agent_id))

    def patch(self, request, agent_id):
        return Response(commands.update(request.tenant_context, agent_id, self.body(request), request=request))

    def delete(self, request, agent_id):
        commands.delete(request.tenant_context, agent_id, request=request)
        return Response(status=204)


class AgentCardToolsView(AgentCardView):
    required_capability = "ai.view"

    def get(self, request, agent_id):
        return Response(queries.tools(request.tenant_context, agent_id))


class _AgentCardStatusView(AgentCardView):
    required_capability = "ai.manage"
    target_active: bool

    def post(self, request, agent_id):
        return Response(commands.set_active(request.tenant_context, agent_id, self.target_active))


class AgentCardActivateView(_AgentCardStatusView):
    target_active = True


class AgentCardDeactivateView(_AgentCardStatusView):
    target_active = False


class AgentCardConnectionsView(AgentCardView):
    required_capability = "integrations.manage"

    def post(self, request, agent_id):
        return Response(commands.bind(request.tenant_context, agent_id, self.body(request), request=request))


class AgentCardConnectionDetailView(AgentCardView):
    required_capability = "integrations.manage"

    def delete(self, request, agent_id, integration_id):
        return Response(commands.unbind(request.tenant_context, agent_id, integration_id, request=request))
