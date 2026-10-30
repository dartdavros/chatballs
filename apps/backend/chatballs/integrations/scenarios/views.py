"""OWNER/ADMIN editing API. No endpoint in this module runs a scenario."""

from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios import presets, services
from chatballs.integrations.scenarios.catalog import definition_context
from chatballs.integrations.scenarios.payloads import issue_payload, scenario_payload
from chatballs.integrations.scenarios.validation import validate_definition
from chatballs.integrations.scenarios.external_keys import key_payload, synchronize_keys
from chatballs.integrations.service_connections.views import invalid


class ScenarioAPIView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def handle_exception(self, exc):
        if isinstance(exc, (ScenarioDefinition.DoesNotExist, Integration.DoesNotExist)):
            return Response({"detail": t("scenarios.not_found")}, status=404)
        if isinstance(exc, services.RevisionConflict):
            return Response({"detail": t("scenarios.conflict")}, status=409)
        if isinstance(exc, ValidationError):
            return invalid(exc)
        return super().handle_exception(exc)

    def rows(self, request):
        return ScenarioDefinition.objects.filter(organization_id=request.tenant_context.organization_id)

    def audit(self, request, row, action):
        record_audit_event(action=f"integrations.scenario_{action}", actor=request.user,
                           organization=request.tenant_context.organization, object_type="ScenarioDefinition",
                           object_id=str(row.public_id), payload={"revision": row.revision}, request=request)

    def save(self, request, public_id=None):
        data = request.data
        allowed = {"name", "definition", "revision", "enabled"}
        if not isinstance(data, dict) or set(data) - allowed or not isinstance(data.get("enabled", False), bool):
            raise ValidationError({"definition": t("scenarios.invalid_definition")})
        row, issues = services.save_definition(tenant=request.tenant_context, name=data.get("name"),
            document=data.get("definition"), revision=data.get("revision"), public_id=public_id,
            enabled=data.get("enabled", False))
        if row is None:
            return Response({"issues": [issue_payload(issue) for issue in issues]}, status=400)
        self.audit(request, row, "saved")
        payload = scenario_payload(row, issues=issues)
        payload["externalKeys"] = synchronize_keys(request, row)
        return Response({"scenario": payload}, status=200 if public_id else 201)


class ScenarioListView(ScenarioAPIView):
    def get(self, request):
        rows = self.rows(request).order_by("name", "id")
        connection = request.query_params.get("connection")
        if connection:
            if not connection.isdecimal():
                raise Http404
            rows = rows.filter(connections__integration_id=int(connection))
        return Response({"items": [scenario_payload(row, detail=False) for row in rows]})

    def post(self, request):
        return self.save(request)


class ScenarioDetailView(ScenarioAPIView):
    def get(self, request, public_id):
        row = self.rows(request).get(public_id=public_id)
        issues = validate_definition(row.definition, context=definition_context(row.organization_id, excluding=public_id))
        payload = scenario_payload(row, issues=issues)
        payload["externalKeys"] = [key_payload(request, key) for key in row.external_keys.all()]
        return Response({"scenario": payload})

    def put(self, request, public_id):
        return self.save(request, public_id)

    def delete(self, request, public_id):
        row = self.rows(request).get(public_id=public_id)
        revision = request.data.get("revision") if isinstance(request.data, dict) else None
        services.delete_definition(tenant=request.tenant_context, public_id=public_id, revision=revision)
        self.audit(request, row, "deleted")
        return Response(status=204)


class ScenarioCheckView(ScenarioAPIView):
    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        context = definition_context(request.tenant_context.organization_id)
        issues = validate_definition(data.get("definition"), context=context)
        return Response({"issues": [issue_payload(issue) for issue in issues], "valid": not issues})


class ScenarioCopyView(ScenarioAPIView):
    def post(self, request, public_id):
        data = request.data if isinstance(request.data, dict) else {}
        row, issues = services.copy_definition(tenant=request.tenant_context, source=public_id, name=data.get("name"))
        self.audit(request, row, "copied")
        payload = scenario_payload(row, issues=issues)
        payload["externalKeys"] = synchronize_keys(request, row)
        return Response({"scenario": payload}, status=201)


class ScenarioPresetView(ScenarioAPIView):
    def post(self, request, connection_id, key):
        row, issues = presets.copy_preset(tenant=request.tenant_context, connection_id=connection_id, key=key)
        self.audit(request, row, "copied")
        payload = scenario_payload(row, issues=issues)
        payload["externalKeys"] = synchronize_keys(request, row)
        return Response({"scenario": payload}, status=201)
