"""Manual one-step execution uses the same snapshot service as direct actions."""

from rest_framework.response import Response

from chatballs.identity.audit import record_audit_event
from chatballs.integrations.execution.launch import launch, launch_direct

# Public import retained for existing metadata consumers.
from chatballs.integrations.execution.manual_catalog_queries import parameter_schema  # noqa: F401
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.views import RunAPIView


class ManualActionsView(RunAPIView):
    def get(self, request):
        from chatballs.integrations.execution.manual_catalog_queries import catalog
        return Response(catalog(request.tenant_context, request.query_params))

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        preview = data.get("preview") is True
        confirmation = data.get("confirmation")
        if data.get("kind") == "operation":
            run, created = launch_direct(tenant=request.tenant_context, connection_id=data.get("connectionId"),
                operation_key=data.get("operationKey", ""), trigger_key=data.get("triggerKey"),
                arguments=data.get("parameters", {}), conversation_id=data.get("conversationId"), preview=preview, confirmation=confirmation)
        else:
            run, created = launch(tenant=request.tenant_context, scenario_id=data.get("scenarioId"),
                trigger_key=data.get("triggerKey"), parameters=data.get("parameters", {}), conversation_id=data.get("conversationId"), preview=preview, confirmation=confirmation)
        if preview:
            return Response({"preview": run})
        if created:
            record_audit_event(action="integrations.run_created", actor=request.user,
                organization=request.tenant_context.organization, object_type="ScenarioRun", object_id=str(run.public_id))
        return Response({"run": run_payload(run, detail=True, tenant=request.tenant_context)}, status=201 if created else 200)
