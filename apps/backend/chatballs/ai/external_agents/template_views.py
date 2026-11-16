"""Export schema and purpose only; skill source/instructions are never serialized."""

from rest_framework.response import Response

from chatballs.ai.external_agents.auth import authenticated, authorize_session
from chatballs.ai.external_agents.contracts import validate
from chatballs.ai.external_agents.formatted_replies import catalog
from chatballs.ai.external_agents.views import ProtocolView


class TemplateView(ProtocolView):
    def get(self, request, connection_id, conversation_id):
        with authenticated(request.headers.get("Authorization")) as (context, connection):
            self.check_connection(connection, connection_id)
            session = authorize_session(context, connection, conversation_id=conversation_id,
                authorization_id=request.query_params.get("authorizationId"), operation="reply-templates")
            result = catalog(session.agent.external_binding)
            validate("catalogs.yaml", "TemplateCatalog", result)
        return Response(result)
