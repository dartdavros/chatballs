from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai import content_link_commands as commands
from chatballs.ai.api_errors import validation_error_response
from chatballs.ai.models import AIAgent
from chatballs.api.permissions import HasCapability
from chatballs.i18n import t


class _ContentCommandView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"

    def handle_exception(self, error):
        if isinstance(error, ValidationError):
            return validation_error_response(error)
        if isinstance(error, AIAgent.DoesNotExist):
            return Response({"detail": t("ai.agent_not_found")}, status=404)
        return super().handle_exception(error)


class KnowledgeBulkMoveView(_ContentCommandView):
    def post(self, request):
        return Response(commands.move(request.tenant_context, request.data, request=request))


class AgentKnowledgeLinkView(_ContentCommandView):
    def post(self, request):
        return Response(commands.link(request.tenant_context, request.data, request=request))


class AgentPortalArticleLinkView(_ContentCommandView):
    def post(self, request):
        return Response(commands.link(request.tenant_context, request.data, articles=True, request=request))


class AgentCategoryKnowledgeSelectView(_ContentCommandView):
    def post(self, request, agent_id):
        return Response(commands.select_category(request.tenant_context, agent_id, request.data, request=request))
