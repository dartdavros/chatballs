"""Entity link HTTP adapters; search launches the ordinary scoped operation."""

from django.http import Http404
from rest_framework.response import Response

from chatballs.integrations.execution.launch import launch_direct
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.views import RunAPIView
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.integrations.scenarios import entity_link_management as management


class EntityLinksView(RunAPIView):
    def handle_exception(self, exc):
        if isinstance(exc, EntityLink.DoesNotExist):
            raise Http404 from exc
        return super().handle_exception(exc)

    def get(self, request):
        return Response(management.listing(request.tenant_context, request.query_params.get("conversation", "")))


class EntityLinkSearchView(EntityLinksView):
    def post(self, request, pk):
        conversation, row, entity = management.linked(request.tenant_context,
            request.query_params.get("conversation", ""), pk, "conversations.operate")
        query = request.data.get("query")
        if not entity.references or not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
            raise ExecutionDenied("arguments")
        run, _ = launch_direct(tenant=request.tenant_context, connection_id=row.integration_id,
            operation_key=entity.references.operation, trigger_key=request.data.get("triggerKey"),
            arguments=entity.references.arguments(query.strip()), conversation_id=conversation.pk)
        return Response({"runId": str(run.public_id)}, status=202)

    def get(self, request, pk):
        return Response(management.search_results(request.tenant_context,
            request.query_params.get("conversation", ""), pk, request.query_params.get("run")))


class EntityLinkCommandView(EntityLinkSearchView):
    def post(self, request, pk):
        return Response(management.change(request.tenant_context, request.query_params.get("conversation", ""),
            pk, request.data, request=request))
