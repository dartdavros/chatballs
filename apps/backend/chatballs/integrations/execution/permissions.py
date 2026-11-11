"""Current principal and context checks, reused before every new effect."""

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.models import Conversation
from chatballs.identity.group_models import member_group_ids
from chatballs.identity.models import EmployeeRole, OrganizationMembership
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.tenancy.context import TenantContext


class ExecutionDenied(ValueError):
    """A safe code; never carries remote responses or operational values."""


def current_actor(tenant):
    if tenant.membership is None or tenant.actor_user is None:
        raise ExecutionDenied("permission")
    member = OrganizationMembership.objects.select_related("user").filter(
        pk=tenant.membership.pk, organization_id=tenant.organization_id,
        user_id=tenant.actor_user.pk, blocked_at__isnull=True, user__is_active=True,
    ).first()
    if member is None:
        raise ExecutionDenied("permission")
    return TenantContext(organization=tenant.organization, membership=member,
                         actor_user=member.user, actor_kind=tenant.actor_kind,
                         correlation_id=tenant.correlation_id)


def authorize(tenant, document, conversation_id=None, *, scenario_id=None, trigger_kind="staff"):
    tenant = current_actor(tenant)
    if scenario_id is not None:
        current = ScenarioDefinition.objects.filter(pk=scenario_id, organization_id=tenant.organization_id).first()
        if current is None or not current.enabled:
            raise ExecutionDenied("scenario_disabled")
        if not any(trigger["kind"] == trigger_kind for trigger in current.definition["triggers"]):
            raise ExecutionDenied("permission")
        # Runtime snapshot is immutable, but revocation applies immediately.
        policies = (document["access"], current.definition["access"])
    else:
        policies = (document["access"],)
    member = tenant.membership
    manager = member.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}
    for policy in policies:
        allowed = member.user_id in policy["staff"] or bool(member_group_ids(member) & set(policy["groups"]))
        if not manager and not allowed:
            raise ExecutionDenied("permission")
        if policy["scope"] == "organization" and not manager:
            from chatballs.integrations.action_catalog.permissions import organization_grants_cover
            if not organization_grants_cover(tenant, document):
                raise ExecutionDenied("permission")
        if policy["scope"] != "organization" and conversation_id is None:
            raise ExecutionDenied("context")
    conversation = None
    if conversation_id is not None:
        conversation = Conversation.objects.select_related("contact", "channel").filter(
            pk=conversation_id, organization_id=tenant.organization_id, archived_at__isnull=True,
        ).first()
        if conversation is None:
            raise ExecutionDenied("context")
        try:
            from chatballs.integrations.execution.snapshots import walk
            capability = "conversations.operate" if any(
                b["kind"] == "action" and b.get("target", "").startswith("service:")
                for b in walk(document["steps"])
            ) else "conversations.view"
            require_conversation_action(tenant, conversation, capability)
        except Conversation.DoesNotExist:
            raise ExecutionDenied("permission") from None
        if any(p["scope"] == "contact" for p in policies) and not conversation.contact_id:
            raise ExecutionDenied("context")
    return tenant, conversation


def authorize_run(tenant, run, *, check_conditions=True):
    from chatballs.webchat.proactive_guards import authorize_run as authorize_site_run
    authorize_site_run(tenant, run)
    if run.definition.get("ai"):
        from chatballs.integrations.execution.ai_policy import authorize_ai
        return authorize_ai(tenant, run)
    if run.definition.get("kind") == "synchronization":
        from chatballs.integrations.scenarios.synchronization_access import authorize_exchange
        result = authorize_exchange(tenant, run)
    elif run.definition.get("kind") == "direct":
        from chatballs.integrations.scenario_state.grants import ActionGrant
        tenant = current_actor(tenant)
        grant_id = run.definition.get("grantId")
        if grant_id is not None:
            step = run.steps.get()
            target = ({"integration__isnull": True, "native_key": step.operation_key, "operation_key": ""}
                if step.adapter_key == "chatballs" else {"integration_id": step.integration_id, "operation_key": step.operation_key})
            grant = ActionGrant.objects.filter(pk=grant_id, organization_id=tenant.organization_id,
                membership=tenant.membership, enabled=True, **target).first()
            if grant is None or grant.scope != run.definition["document"]["access"]["scope"]:
                raise ExecutionDenied("permission")
        elif tenant.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
            raise ExecutionDenied("permission")
        result = authorize(tenant, run.definition["document"], run.conversation_id)
    else:
        if run.scenario_id is None:
            raise ExecutionDenied("scenario_disabled")
        from chatballs.integrations.execution.principals import authorize_chain
        result = authorize_chain(tenant, run)
    current_tenant, conversation = result
    expected_contact = run.definition.get("context", {}).get("contact", {}).get("id")
    if conversation and expected_contact != (str(conversation.contact_id) if conversation.contact_id else None):
        raise ExecutionDenied("context_changed")
    from chatballs.integrations.execution.conditions import require_conditions
    from chatballs.integrations.scenarios.values import RunValues
    if check_conditions:
        require_conditions(run.definition["document"], conversation, run.definition["parameters"],
            values=RunValues(parameters=run.definition["parameters"], context=context_values(conversation), event=run.definition.get("event", {})))
    return current_tenant, conversation


def view_run(tenant, run):
    tenant = current_actor(tenant)
    if tenant.membership.role in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
        return tenant
    if run.conversation_id:
        conversation = Conversation.objects.get(pk=run.conversation_id, organization_id=tenant.organization_id)
        try:
            require_conversation_action(tenant, conversation, "conversations.view")
            return tenant
        except Conversation.DoesNotExist:
            pass
    raise ExecutionDenied("permission")


def context_values(conversation):
    if conversation is None:
        return {}
    values = {"conversation": {"id": str(conversation.pk), "channel": str(conversation.channel_id),
                               "status": conversation.lifecycle.lower()}}
    if conversation.contact_id:
        contact = conversation.contact
        values["contact"] = {"id": str(contact.pk), "name": contact.name,
                             "phone": contact.phone, "email": contact.email}
    return values


def direct_policy(tenant, connection_id, operation_key, conversation_id):
    from chatballs.integrations.scenario_state.grants import ActionGrant
    from chatballs.integrations.scenarios.definition import empty_definition
    tenant = current_actor(tenant)
    target = ({"integration__isnull": True, "native_key": operation_key, "operation_key": ""}
        if connection_id == "chatballs" else {"integration_id": connection_id, "operation_key": operation_key})
    grant = ActionGrant.objects.filter(organization_id=tenant.organization_id, membership=tenant.membership,
        enabled=True, **target).first()
    if tenant.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN} and grant is None:
        raise ExecutionDenied("permission")
    document = empty_definition()
    namespace = "chatballs" if connection_id == "chatballs" else "service"
    document["steps"] = [{"id": "operation", "kind": "action", "connection": str(connection_id),
        "target": f"{namespace}:{operation_key}", "inputs": {}}]
    native = None
    if connection_id == "chatballs":
        from chatballs.integrations.action_catalog.registry import native_action
        native = native_action(operation_key)
    document["access"].update(staff=[tenant.actor_user.pk], scope=grant.scope if grant else (
        "organization" if native and native.scope == "organization" else
        "conversation" if conversation_id is not None else "organization"))
    tenant, conversation = authorize(tenant, document, conversation_id)
    return tenant, document, grant, conversation


def allowed_files(tenant, conversation_id=None):
    from chatballs.integrations.models import ServiceFile
    rows = ServiceFile.objects.filter(organization_id=tenant.organization_id)
    if tenant.membership is None or tenant.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
        rows = rows.filter(execution_owners__step__run__conversation_id=conversation_id) if conversation_id else rows.none()
    return rows.distinct()


def validate_arguments(tenant, conversation_id, operation, arguments):
    from chatballs.integrations.scenarios.values import RunValues, prepare_inputs
    files = {str(pk) for pk in allowed_files(tenant, conversation_id).values_list("public_id", flat=True)}
    return prepare_inputs(operation.input, {name: {"source": "constant", "value": value} for name, value in arguments.items()}, RunValues(files=files))
