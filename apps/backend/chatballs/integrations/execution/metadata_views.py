from rest_framework.response import Response

from chatballs.integrations.execution.metadata import metadata_action, lookup_keys
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.views import RunAPIView
from chatballs.integrations.service_connections.binding import load_lookup
from chatballs.tenancy.database import tenant_atomic


class ManualLookupView(RunAPIView):
    tenant_manages_own_transaction = True

    def initial(self, request, *args, **kwargs):
        with tenant_atomic(request.tenant_context):
            super().initial(request, *args, **kwargs)

    def get(self, request):
        data = request.query_params
        connection_id, conversation_id = int(data["connection"]), int(data["conversation"])
        with tenant_atomic(request.tenant_context):
            integration, _row, _adapter, _method, operation = metadata_action(request.tenant_context,
                connection_id=connection_id, operation_key=data.get("operation", ""), conversation_id=conversation_id,
                scenario_id=data.get("scenario"))
            if data.get("lookup") not in lookup_keys(operation.input):
                raise ExecutionDenied("permission")
        items = load_lookup(tenant=request.tenant_context, integration=integration, key=data["lookup"])
        return Response({"items": [{"value": item.value, "label": item.label} for item in items]})
