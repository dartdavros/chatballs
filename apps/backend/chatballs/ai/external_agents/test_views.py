"""Administrative test API; never accepts a customer conversation identifier."""

from django.http import FileResponse, Http404
from rest_framework.response import Response

from chatballs.ai.external_agents import test_chat
from chatballs.ai.external_agents.config_policy import invalid
from chatballs.ai.external_agents.config_views import SettingsView
from chatballs.ai.external_agents.settings_catalog import catalog
from chatballs.conversations.models import Message
from chatballs.tenancy.database import tenant_atomic

# These product API views are exercised by the dedicated settings and scope tests.
__test__ = False


class TestDefinitionView(SettingsView):
    def get(self, request, channel_id):
        with tenant_atomic(request.tenant_context):
            agent = test_chat.agent_for(request.tenant_context, channel_id)
            binding = agent.external_binding
            definitions = catalog(request.tenant_context)
            return Response({"standardFields": binding.standard_fields,
                             "customFields": [field for field in definitions["customFields"]
                                              if {"sourceConnectionId": field["sourceConnectionId"],
                                                  "fieldId": field["fieldId"]} in binding.custom_fields]})

    def post(self, request, channel_id):
        try:
            return Response(test_chat.start(request.tenant_context, channel_id, request.data), status=201)
        except (ValueError, TypeError, KeyError):
            invalid()


class TestSessionView(SettingsView):
    def get(self, request, channel_id, scope_id):
        return Response(test_chat.read(request.tenant_context, channel_id, scope_id))

    def post(self, request, channel_id, scope_id):
        return Response(test_chat.send(request.tenant_context, channel_id, scope_id, request.data), status=202)

    def delete(self, request, channel_id, scope_id):
        test_chat.close(request.tenant_context, channel_id, scope_id)
        return Response(status=204)


class TestFileView(SettingsView):
    def get(self, request, channel_id, scope_id, message_id):
        with tenant_atomic(request.tenant_context):
            scope = test_chat.scope_for(request.tenant_context, channel_id, scope_id)
            from chatballs.ai.external_agents.test_scope import active_scope

            active_scope(scope.conversation, scope.agent, require_control=False)
            message = Message.including_tests.filter(
                conversation_id=scope.conversation_id, pk=message_id, audio="",
                externalagentdeliveryitem__state="transport_accepted",
            ).first()
            if message is None or not message.attachment:
                raise Http404
            response = FileResponse(message.attachment.open("rb"), as_attachment=True,
                                    filename=message.attachment_name, content_type=message.attachment_content_type)
            response["X-Content-Type-Options"] = "nosniff"
            return response
