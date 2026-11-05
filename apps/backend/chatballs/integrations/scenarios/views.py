"""HTTP adapters for definition management; no endpoint here launches a run."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios import management, services
from chatballs.integrations.scenarios.payloads import issue_payload
from chatballs.integrations.service_connections.views import invalid


class ScenarioAPIView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def handle_exception(self, exc):
        if isinstance(exc, ScenarioDefinition.DoesNotExist | Integration.DoesNotExist):
            return Response({"detail": t("scenarios.not_found")}, status=404)
        if isinstance(exc, services.RevisionConflict):
            return Response({"detail": t("scenarios.conflict")}, status=409)
        if isinstance(exc, management.InvalidDefinition):
            return Response({"issues": [issue_payload(issue) for issue in exc.issues]}, status=400)
        if isinstance(exc, ValidationError):
            return invalid(exc)
        return super().handle_exception(exc)

    def rows(self, request):
        return management.rows(request.tenant_context)

    def audit(self, request, row, action):
        management.audit(request.tenant_context, row, action, request)

    def save(self, request, public_id=None):
        return Response(management.save(request.tenant_context, request.data, public_id=public_id, request=request),
            status=200 if public_id else 201)


class ScenarioListView(ScenarioAPIView):
    def get(self, request):
        return Response(management.listing(request.tenant_context, connection=request.query_params.get("connection", "")))

    def post(self, request):
        return self.save(request)


class ScenarioDetailView(ScenarioAPIView):
    def get(self, request, public_id):
        return Response(management.detail(request.tenant_context, public_id, request=request))

    def put(self, request, public_id):
        return self.save(request, public_id)

    def delete(self, request, public_id):
        revision = request.data.get("revision") if isinstance(request.data, dict) else None
        management.delete(request.tenant_context, public_id, revision, request=request)
        return Response(status=204)


class ScenarioCheckView(ScenarioAPIView):
    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        return Response(management.check(request.tenant_context, data.get("definition")))


class ScenarioCopyView(ScenarioAPIView):
    def post(self, request, public_id):
        data = request.data if isinstance(request.data, dict) else {}
        return Response(management.copy(request.tenant_context, public_id, data.get("name"), request=request), status=201)


class ScenarioPresetView(ScenarioAPIView):
    def post(self, request, connection_id, key):
        return Response(management.preset(request.tenant_context, connection_id, key, request=request), status=201)
