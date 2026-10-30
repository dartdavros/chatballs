from rest_framework.response import Response

from chatballs.i18n import t
from chatballs.ai.models import AIAgent
from chatballs.identity.models import EmployeeGroup, OrganizationMembership
from chatballs.integrations.models import ServiceFile, Integration, IntegrationKind
from chatballs.conversations.models import ConversationLabel
from chatballs.integrations.action_catalog.registry import action_schemas
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.scenarios.catalog import definition_context
from chatballs.integrations.scenarios.views import ScenarioAPIView
from chatballs.integrations.scenarios.native_events import NATIVE_EVENTS
from chatballs.integrations.service_connections.payloads import field_payload


class ScenarioCatalogView(ScenarioAPIView):
    def get(self, request):
        context = definition_context(request.tenant_context.organization_id)
        return Response({
            "transforms": [{"key": extension.ref, "title": t(extension.implementation.title_key),
                "inputTypes": sorted(extension.implementation.input_types), "outputType": extension.implementation.output_type,
                "arguments": field_payload("", extension.implementation.arguments)}
                for extension in default_registry().extensions("transform")],
            "timezone": request.tenant_context.organization.timezone,
            "labels": list(ConversationLabel.objects.filter(organization_id=request.tenant_context.organization_id).values("id", "name")),
            "channels": list(Integration.objects.filter(organization_id=request.tenant_context.organization_id, kind=IntegrationKind.MESSENGER).values("id", "name")),
            "groups": list(EmployeeGroup.objects.filter(organization_id=request.tenant_context.organization_id).values("id", "name")),
            "staff": [{"id": member.user_id, "name": member.user.full_name or member.user.email}
                for member in OrganizationMembership.objects.filter(organization_id=request.tenant_context.organization_id, blocked_at__isnull=True).select_related("user")],
            "agents": list(AIAgent.objects.filter(organization_id=request.tenant_context.organization_id).values("id", "name")),
            "files": [{"id": str(row.public_id), "name": row.name} for row in ServiceFile.objects.filter(organization_id=request.tenant_context.organization_id)],
            "events": [{"key": key, "title": t(title), "payload": field_payload("", schema)} for key, title, schema in NATIVE_EVENTS],
            "context": field_payload("", context.context),
            "entities": [{"key": key, "title": t(f"scenarios.{key}"), "fields": field_payload("", schema),
                "writableFields": sorted(context.writable_fields.get((connection, key), set()))}
                for (connection, key), schema in context.entities.items() if connection == "chatballs"],
            "nativeActions": [{"key": f"chatballs:{action.key}", "title": t(action.title_key),
                "input": field_payload("", action.input), "output": field_payload("", action.output)}
                for action in action_schemas()],
            "scenarios": [{"id": str(row.public_id), "name": row.name,
                "parameters": row.definition["parameters"], "results": row.definition["results"]}
                for row in self.rows(request).order_by("name")],
        })
