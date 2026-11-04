"""Current agent authority, shared by launch, effects and result reads."""

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.conversations.models import Conversation
from chatballs.ai.execution_version import configuration_version
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.tenancy.context import TenantContext


def current(tenant, binding):
    organization = lock_organization(tenant.organization_id)
    grant = AgentActionGrant.objects.select_related("agent__channel", "scenario").filter(
        pk=binding["grant"], organization_id=organization.pk, agent_id=binding["agent"],
        revision=binding["revision"], mode=binding["mode"],
    ).exclude(mode="off").first()
    if grant is None:
        raise ExecutionDenied("permission")
    if binding.get("agentVersion") != configuration_version(grant.agent):
        raise ExecutionDenied("permission")
    if binding.get("tester"):
        from chatballs.identity.models import EmployeeRole, OrganizationMembership
        member = OrganizationMembership.objects.select_related("organization", "user").filter(
            pk=binding["tester"], organization_id=organization.pk, blocked_at__isnull=True, user__is_active=True,
            role__in=(EmployeeRole.OWNER, EmployeeRole.ADMIN)).first()
        if (member is None or organization.operation_mode_version != binding["modeVersion"]
                or not autonomous_allowed(grant.agent.channel, organization=organization)):
            raise ExecutionDenied("permission")
        conversation = None
    else:
        conversation = _conversation(organization, grant, binding)
    if grant.scenario_id:
        scenario = grant.scenario
        if not scenario.enabled or not any(t["kind"] == "ai" and grant.agent_id in t.get("agents", []) for t in scenario.definition["triggers"]):
            raise ExecutionDenied("scenario_disabled")
    return grant, conversation


def _conversation(organization, grant, binding):
    conversation = Conversation.objects.select_for_update(of=("self",)).select_related(
        "contact", "connection", "channel__ai_agent__provider_integration",
    ).filter(pk=binding["conversation"], organization_id=organization.pk, archived_at__isnull=True).first()
    if (conversation is None or conversation.channel_id != grant.agent.channel_id
            or conversation.ai_control_version != binding["controlVersion"]
            or organization.operation_mode_version != binding["modeVersion"]
            or not autonomous_allowed(conversation.channel, organization=organization,
                                      connection=conversation.connection, conversation=conversation)):
        raise ExecutionDenied("context_changed")
    return conversation


def bind(grant, conversation):
    return {"grant": grant.pk, "agent": grant.agent_id, "revision": grant.revision, "mode": grant.mode,
            "agentVersion": configuration_version(grant.agent),
            "conversation": conversation.pk, "controlVersion": conversation.ai_control_version,
            "modeVersion": conversation.organization.operation_mode_version}


def authorize_ai(tenant, run):
    binding = run.definition["ai"]
    grant, conversation = current(tenant, binding)
    # A grant cannot be retargeted to authorize an older invocation.
    root = run
    while root.parent_id:
        root = root.parent
    if grant.scenario_id != root.scenario_id:
        raise ExecutionDenied("permission")
    if grant.integration_id:
        step = root.steps.get()
        if step.integration_id != grant.integration_id or step.operation_key != grant.operation_key:
            raise ExecutionDenied("permission")
    cursor = run
    while cursor:
        if cursor.cancel_requested_at or cursor.data_cleared_at:
            raise ExecutionDenied("permission")
        if cursor.scenario_id:
            scenario = cursor.scenario
            trigger = "scenario" if cursor.parent_id else "ai"
            if (not scenario.enabled or not any(t["kind"] == trigger for t in scenario.definition["triggers"])
                    or cursor.parent_id and (not scenario.definition["access"]["delegated"]
                        or not cursor.definition["document"]["access"]["delegated"])):
                raise ExecutionDenied("permission")
        from chatballs.integrations.execution.conditions import require_conditions
        require_conditions(cursor.definition["document"], conversation, cursor.definition["parameters"])
        cursor = cursor.parent if cursor.parent_id else None
    expected = run.definition.get("context", {}).get("contact", {}).get("id")
    if conversation and expected != (str(conversation.contact_id) if conversation.contact_id else None):
        raise ExecutionDenied("context_changed")
    return TenantContext.for_resource(tenant.organization), conversation


def approver(tenant, run):
    tenant = current_actor(tenant)
    _, conversation = authorize_ai(tenant, run)
    from chatballs.conversations.access import require_conversation_action
    from chatballs.identity.models import EmployeeRole
    if conversation:
        try:
            require_conversation_action(tenant, conversation, "conversations.operate")
        except Conversation.DoesNotExist:
            raise ExecutionDenied("permission") from None
    elif tenant.membership_id != run.definition["ai"].get("tester"):
        raise ExecutionDenied("permission")
    if (tenant.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
            and (conversation is None or conversation.assigned_operator_id != tenant.actor_user.pk)):
        raise ExecutionDenied("permission")
    expires = parse_datetime(run.definition["ai"]["approvalDeadline"])
    if expires <= timezone.now():
        raise ExecutionDenied("approval_expired")
    return tenant


def needs_confirmation(run, operation):
    if run.definition.get("ai"):
        return run.definition["ai"]["mode"] == "ask"
    from chatballs.integrations.execution.automation import confirmation_required
    return confirmation_required(operation, run)
