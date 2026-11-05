from django.core.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai import knowledge_commands as commands
from chatballs.ai.api_errors import validation_error_response
from chatballs.ai.knowledge_api_inputs import knowledge_filters
from chatballs.ai.knowledge_reads import get_knowledge, list_knowledge
from chatballs.ai.models import Knowledge
from chatballs.api.permissions import HasCapability
from chatballs.i18n import t


class _KnowledgeBaseView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "ai.view", "POST": "ai.manage",
        "PATCH": "ai.manage", "DELETE": "ai.manage"}

    def handle_exception(self, error):
        if isinstance(error, ValidationError):
            return validation_error_response(error)
        if isinstance(error, Knowledge.DoesNotExist):
            return Response({"detail": t("ai.knowledge_not_found")}, status=404)
        return super().handle_exception(error)


class KnowledgeListCreateView(_KnowledgeBaseView):
    def get(self, request):
        return Response(list_knowledge(request.tenant_context, knowledge_filters(request),
            request.query_params))

    def post(self, request):
        return Response(commands.create(request.tenant_context, request.data, request=request), status=201)


class KnowledgeDetailView(_KnowledgeBaseView):
    def get(self, request, knowledge_id):
        return Response(get_knowledge(request.tenant_context, knowledge_id))

    def patch(self, request, knowledge_id):
        return Response(commands.update(request.tenant_context, knowledge_id, request.data, request=request))

    def delete(self, request, knowledge_id):
        commands.delete(request.tenant_context, knowledge_id, request=request)
        return Response(status=204)


class KnowledgeImportView(_KnowledgeBaseView):
    def post(self, request):
        return Response(commands.import_documents(request.tenant_context,
            request.data.get("documents"), request=request), status=201)


class KnowledgeReindexView(_KnowledgeBaseView):
    def post(self, request, knowledge_id):
        return Response(commands.reindex(request.tenant_context, knowledge_id, request=request))


class KnowledgeAttachmentUploadView(_KnowledgeBaseView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, knowledge_id):
        return Response(commands.upload_attachment(request.tenant_context, knowledge_id,
            request.FILES.get("file"), request=request), status=201)


class KnowledgeAttachmentDeleteView(_KnowledgeBaseView):
    def delete(self, request, knowledge_id, attachment_id):
        commands.remove_attachment(request.tenant_context, knowledge_id, attachment_id, request=request)
        return Response(status=204)
