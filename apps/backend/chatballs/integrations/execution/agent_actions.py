"""Explicit policy editing; neither catalog reads nor migration grant access."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.models import AIAgent
from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.operation_modes import lock_organization
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration, IntegrationKind
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition


def catalog(organization_id, agent):
    policies = list(agent.action_grants.all())
    grants = {(g.integration_id, g.operation_key, g.scenario_id): g for g in policies if not g.native_key}
    rows = []
    registry = default_registry()
    for connection in Integration.objects.filter(organization_id=organization_id, kind=IntegrationKind.SERVICE).select_related("service_settings"):
        settings = getattr(connection, "service_settings", None)
        adapter = registry.adapter(settings.adapter_key) if settings else None
        if adapter is None or adapter.contract_version != settings.adapter_version:
            continue
        for operation in adapter.operations:
            grant = grants.get((connection.pk, operation.key, None))
            rows.append({"id": f"operation:{connection.pk}:{operation.key}", "title": t(operation.title_key),
                "subtitle": connection.name, "mode": grant.mode if grant else "off", "revision": grant.revision if grant else 0,
                "available": connection.is_active and connection.status == "OK", "writes": operation.effect != "read",
                "integration": connection.pk, "operation": operation.key, "scenario": None})
    for scenario in ScenarioDefinition.objects.filter(organization_id=organization_id, enabled=True):
        if not any(tr["kind"] == "ai" and agent.pk in tr.get("agents", []) for tr in scenario.definition["triggers"]):
            continue
        grant = grants.get((None, "", scenario.pk))
        rows.append({"id": f"scenario:{scenario.public_id}", "title": scenario.name, "subtitle": t("runs.scenario"),
            "mode": grant.mode if grant else "off", "revision": grant.revision if grant else 0,
            "available": True, "writes": True, "integration": None, "operation": "", "scenario": scenario.pk})
    from chatballs.integrations.execution.native_principal import native_catalog
    rows.extend(native_catalog({g.native_key: g for g in policies if g.native_key}))
    return rows


def change_policy(tenant, agent, target, mode, revision):
    if not isinstance(mode, str) or mode not in {"off", "self", "ask"} or type(revision) is not int:
        raise ExecutionDenied("arguments")
    lock_organization(tenant.organization_id)
    row = next((item for item in catalog(tenant.organization_id, agent) if item["id"] == target), None)
    if row is None or mode != "off" and not row["available"]:
        raise ExecutionDenied("operation_unavailable")
    grant = AgentActionGrant.objects.select_for_update().filter(agent=agent, integration_id=row["integration"],
        scenario_id=row["scenario"], operation_key=row["operation"], native_key=row.get("native", "")).first()
    if revision != (grant.revision if grant else 0):
        raise ExecutionDenied("state_changed")
    if grant is None:
        grant = AgentActionGrant(agent=agent, integration_id=row["integration"], scenario_id=row["scenario"],
            operation_key=row["operation"], native_key=row.get("native", ""))
    elif grant.mode == mode:
        return
    else:
        grant.revision += 1
    from chatballs.integrations.execution.native_principal import capture_delegate
    capture_delegate(tenant, grant, mode)
    grant.mode = mode
    grant.save()
    record_audit_event(action="integrations.agent_action_changed", actor=tenant.actor_user,
        organization=tenant.organization, object_type="AgentActionGrant", object_id=str(grant.pk),
        payload={"mode": mode, "revision": grant.revision})


class AgentActionsView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"

    def get(self, request, channel_id):
        from chatballs.integrations.execution.agent_policy_management import listing
        return Response(listing(request.tenant_context, channel_id))

    def put(self, request, channel_id):
        from chatballs.integrations.execution.agent_policy_management import update
        try:
            return Response(update(request.tenant_context, channel_id, request.data))
        except ExecutionDenied as error:
            from chatballs.integrations.execution.errors import error_message
            return Response({"detail": error_message(str(error))}, status=409)

    def handle_exception(self, exc):
        if isinstance(exc, AIAgent.DoesNotExist):
            return Response(status=404)
        return super().handle_exception(exc)
