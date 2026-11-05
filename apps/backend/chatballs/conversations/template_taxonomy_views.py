"""HTTP adapters for the two fixed reply library taxonomies."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations import template_taxonomy_services as service
from chatballs.conversations.template_models import ReplyTemplateCategory, ReplyTemplateTag
from chatballs.conversations.template_taxonomy_services import taxonomy_payload as taxonomy_payload


class TaxonomyListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"
    model = None

    def get(self, request):
        return Response(service.list_taxonomy(self.model, request.tenant_context))

    def post(self, request):
        return Response(service.create_taxonomy(self.model, request.tenant_context, request.data), status=201)


class TaxonomyDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"
    model = None

    def get(self, request, item_id):
        return Response(service.get_taxonomy(self.model, request.tenant_context, item_id))

    def patch(self, request, item_id):
        return Response(service.update_taxonomy(self.model, request.tenant_context, item_id, request.data))

    def delete(self, request, item_id):
        service.delete_taxonomy(self.model, request.tenant_context, item_id)
        return Response(status=204)


class CategoryListView(TaxonomyListView):
    model = ReplyTemplateCategory


class CategoryDetailView(TaxonomyDetailView):
    model = ReplyTemplateCategory


class TagListView(TaxonomyListView):
    model = ReplyTemplateTag


class TagDetailView(TaxonomyDetailView):
    model = ReplyTemplateTag
