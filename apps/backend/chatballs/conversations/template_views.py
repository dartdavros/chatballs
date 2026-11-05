"""HTTP adapters for the existing reply library services."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations import template_services as service
from chatballs.conversations.template_services import save_template as save_template
from chatballs.conversations.template_services import template_payload as template_payload


class ReplyTemplateListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"

    def get(self, request):
        return Response(service.list_templates(request.tenant_context, request.query_params))

    def post(self, request):
        return Response(service.create_template(request.tenant_context, request.data), status=201)


class ReplyTemplateDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"

    def get(self, request, template_id):
        return Response(service.get_template(request.tenant_context, template_id))

    def patch(self, request, template_id):
        return Response(service.update_template(request.tenant_context, template_id, request.data))

    def delete(self, request, template_id):
        service.delete_template(request.tenant_context, template_id)
        return Response(status=204)
