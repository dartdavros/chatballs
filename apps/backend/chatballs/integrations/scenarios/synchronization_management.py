from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.models import Integration, IntegrationKind
from chatballs.integrations.scenario_state.synchronization import ServiceSynchronizationSettings
from chatballs.integrations.scenarios.catalog import definition_context
from chatballs.integrations.scenarios.management import InvalidDefinition
from chatballs.integrations.scenarios.services import RevisionConflict
from chatballs.integrations.scenarios.synchronization import check_synchronization
from chatballs.integrations.service_connections.management_reads import require
from chatballs.tenancy.database import tenant_atomic


def connection_for(tenant, connection_id, lock=False):
    require(tenant, "integrations.manage")
    rows = Integration.objects.filter(organization_id=tenant.organization_id, kind=IntegrationKind.SERVICE)
    if lock:
        rows = rows.select_for_update()
    return rows.get(id=connection_id)

def detail(tenant, connection_id):
    with tenant_atomic(tenant):
        connection = connection_for(tenant, connection_id)
        row = ServiceSynchronizationSettings.objects.filter(integration=connection).first()
        latest = row.checkpoints.select_related("run").order_by("-run__created_at").first() if row else None
        from chatballs.integrations.execution.errors import error_message
        from chatballs.integrations.execution.payloads import run_payload
        result = run_payload(latest.run) if latest and latest.run else None
        return {"revision": row.revision if row else 0, "definition": row.definition if row else {"version": 1, "synchronization": []},
            "result": result, "error": error_message(latest.error_code) if latest and latest.error_code else ""}

def save(tenant, connection_id, data, *, request=None):
    with tenant_atomic(tenant):
        connection = connection_for(tenant, connection_id, lock=True)
        row = ServiceSynchronizationSettings.objects.filter(integration=connection).first()
        data = data if isinstance(data, dict) else {}
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
            raise InvalidDefinition(issues)
        if any(str(connection_id) not in {str(pair[side]["connection"]) for side in ("left", "right")} for pair in document["synchronization"]):
            raise ValidationError({"definition": t("scenarios.invalid_reference")})
        from chatballs.integrations.scenarios.synchronization_support import require_supported
        require_supported(tenant, document["synchronization"])
        if row is None:
            row = ServiceSynchronizationSettings(organization_id=connection.organization_id, integration=connection)
        else:
            row.revision += 1
        row.definition = document
        row.delegate = tenant.membership if any(pair["enabled"] for pair in document["synchronization"]) else None
        row.save()
        record_audit_event(action="integrations.synchronization_saved", actor=tenant.actor_user,
            organization=tenant.organization, object_type="Integration", object_id=str(connection_id),
            payload={"revision": row.revision}, request=request)
        return {"revision": row.revision, "definition": row.definition}
