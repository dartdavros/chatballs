"""HTTP presentation of shared category commands."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai import category_management as service
from chatballs.ai.api_errors import validation_error_response
from chatballs.api.permissions import HasCapability


class KnowledgeCategoryListCreateView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "ai.view", "POST": "ai.manage"}

    def get(self, request):
        return Response(service.list_categories(request.tenant_context))

    def post(self, request):
        try:
            result = service.create_category(request.tenant_context, request.data, request=request)
        except ValidationError as error:
            return validation_error_response(error)
        return Response(result, status=201)


class KnowledgeCategoryDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"

    def patch(self, request, category_id):
        try:
            result = service.update_category(request.tenant_context, category_id, request.data, request=request)
        except ValidationError as error:
            return validation_error_response(error)
        return Response(result)

    def delete(self, request, category_id):
        try:
            service.delete_category(request.tenant_context, category_id, request=request)
        except ValidationError as error:
            return validation_error_response(error)
        return Response(status=204)
