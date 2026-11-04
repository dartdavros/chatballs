"""Approval editors may read only lookups declared by the frozen operation."""

from rest_framework.response import Response

from chatballs.integrations.execution.ai_policy import approver
from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.metadata import lookup_keys
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.snapshots import check_contract
from chatballs.integrations.execution.views import RunAPIView
from chatballs.integrations.service_connections.binding import load_lookup
from chatballs.tenancy.database import tenant_atomic


class ApprovalLookupView(RunAPIView):
    tenant_manages_own_transaction = True

    def initial(self, request, *args, **kwargs):
        with tenant_atomic(request.tenant_context):
            super().initial(request, *args, **kwargs)

    def get(self, request, public_id):
        with tenant_atomic(request.tenant_context):
            run = self.rows(request).get(public_id=public_id)
            approver(request.tenant_context, run)
            step = run.steps.get(path=request.query_params.get("path"))
            integration, _, adapter, _, operation = resolve_action(run.organization_id, step.integration_id,
                f"service:{step.operation_key}", expected=(step.adapter_key, step.adapter_version))
            check_contract(run, {"connection": str(step.integration_id), "target": f"service:{step.operation_key}"}, operation, adapter)
            lookup = request.query_params.get("lookup")
            if lookup not in lookup_keys(operation.input):
                raise ExecutionDenied("permission")
        items = load_lookup(tenant=request.tenant_context, integration=integration, key=lookup)
        return Response({"items": [{"value": item.value, "label": item.label} for item in items]})
