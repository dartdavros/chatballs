from django.core.exceptions import ValidationError
from rest_framework.response import Response

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.models import Integration, IntegrationKind
from chatballs.integrations.scenario_state.synchronization import ServiceSynchronizationSettings
from chatballs.integrations.scenarios.catalog import definition_context
from chatballs.integrations.scenarios.payloads import issue_payload
from chatballs.integrations.scenarios.services import RevisionConflict
from chatballs.integrations.scenarios.synchronization import check_synchronization
from chatballs.integrations.scenarios.views import ScenarioAPIView


class ServiceSynchronizationView(ScenarioAPIView):
    def connection(self, request, connection_id, lock=False):
        rows = Integration.objects.filter(organization_id=request.tenant_context.organization_id, kind=IntegrationKind.SERVICE)
        if lock:
            rows = rows.select_for_update()
        return rows.get(id=connection_id)

    def get(self, request, connection_id):
        connection = self.connection(request, connection_id)
        row = ServiceSynchronizationSettings.objects.filter(integration=connection).first()
        return Response({"revision": row.revision if row else 0, "definition": row.definition if row else {"version": 1, "synchronization": []}})

    def put(self, request, connection_id):
        connection = self.connection(request, connection_id, lock=True)
        row = ServiceSynchronizationSettings.objects.filter(integration=connection).first()
        data = request.data if isinstance(request.data, dict) else {}
        revision = data.get("revision")
        if type(revision) is not int or revision != (row.revision if row else 0):
            raise RevisionConflict
        document = data.get("definition")
        if not isinstance(document, dict) or set(document) != {"version", "synchronization"} or type(document["version"]) is not int or document["version"] != 1:
            raise ValidationError({"definition": t("scenarios.invalid_definition")})
        issues = []
        try:
            check_synchronization(document["synchronization"], context=definition_context(connection.organization_id), issues=issues)
        except (TypeError, KeyError, AttributeError):
            raise ValidationError({"definition": t("scenarios.invalid_definition")}) from None
        if issues:
            return Response({"issues": [issue_payload(issue) for issue in issues]}, status=400)
        if any(str(connection_id) not in {str(pair[side]["connection"]) for side in ("left", "right")} for pair in document["synchronization"]):
            raise ValidationError({"definition": t("scenarios.invalid_reference")})
        if row is None:
            row = ServiceSynchronizationSettings(organization_id=connection.organization_id, integration=connection)
        else:
            row.revision += 1
        row.definition = document
        row.save()
        record_audit_event(action="integrations.synchronization_saved", actor=request.user,
            organization=request.tenant_context.organization, object_type="Integration", object_id=str(connection_id),
            payload={"revision": row.revision}, request=request)
        return Response({"revision": row.revision, "definition": row.definition})
