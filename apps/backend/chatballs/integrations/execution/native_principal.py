"""An explicitly saved grant delegate; never inferred from the organization."""

from chatballs.identity.models import EmployeeRole, OrganizationMembership
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.execution.snapshots import walk
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.tenancy.context import TenantContext


def has_native(scenario):
    if scenario is None:
        return False
    visited = set()

    def visit(row, depth):
        if depth >= 16 or len(visited) >= 1000:
            raise ExecutionDenied("budget_depth")
        if row.pk in visited:
            return False
        visited.add(row.pk)
        for block in walk(row.definition["steps"]):
            if block["kind"] == "action" and block.get("target", "").startswith("chatballs:"):
                from chatballs.integrations.action_catalog.registry import native_action
                if native_action(block["target"].removeprefix("chatballs:")):
                    return True
            if block["kind"] == "call":
                child = ScenarioDefinition.objects.filter(organization_id=row.organization_id,
                    public_id=block["scenario"]).first()
                if child and visit(child, depth + 1):
                    return True
        return False
    return visit(scenario, 0)


def capture_delegate(tenant, grant, mode):
    """Only an explicit mode change can create or replace this authority."""
    if mode == "off":
        grant.delegate = None
    elif grant.native_key or has_native(grant.scenario):
        actor = current_actor(tenant)
        if actor.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
            raise ExecutionDenied("permission")
        grant.delegate = actor.membership


def delegate_context(tenant, grant, binding):
    if not grant.delegate_id or binding.get("delegate") != grant.delegate_id:
        raise ExecutionDenied("permission")
    member = OrganizationMembership.objects.select_related("organization", "user").filter(
        pk=grant.delegate_id, organization_id=tenant.organization_id,
        role__in=(EmployeeRole.OWNER, EmployeeRole.ADMIN), blocked_at__isnull=True,
        user__is_active=True).first()
    if member is None:
        raise ExecutionDenied("permission")
    return TenantContext.for_membership(member)


def native_catalog(grants):
    from chatballs.i18n import t
    from chatballs.integrations.action_catalog.registry import native_actions
    return [{"id": f"native:{action.key}", "title": t(action.operation.title_key),
        "subtitle": t("native.source"), "mode": grants[action.key].mode if action.key in grants else "off",
        "revision": grants[action.key].revision if action.key in grants else 0,
        "available": True, "writes": action.operation.effect != "read", "integration": None,
        "operation": "", "scenario": None, "native": action.key} for action in native_actions()]
