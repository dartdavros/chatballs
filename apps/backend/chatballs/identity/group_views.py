"""HTTP adapters for the shared organization group service."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.identity import group_services


class GroupListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "employees.view", "POST": "groups.manage"}

    def get(self, request):
        return Response(group_services.list_groups(request.tenant_context))

    def post(self, request):
        return Response(group_services.create_group(request.tenant_context, request.data,
            request=request), status=201)


class GroupDetailView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"PATCH": "groups.manage", "DELETE": "groups.manage"}

    def patch(self, request, group_id):
        return Response(group_services.update_group(request.tenant_context, group_id,
            request.data, request=request))

    def delete(self, request, group_id):
        return Response(group_services.delete_group(request.tenant_context, group_id,
            request=request))
