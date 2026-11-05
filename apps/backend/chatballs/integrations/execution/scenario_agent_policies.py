"""The scenario editor changes the same agent/target grants as the agent card."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.identity.operation_modes import lock_organization
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant


def payload(scenario):
    return [{"agent": grant.agent_id, "mode": grant.mode, "revision": grant.revision}
            for grant in AgentActionGrant.objects.filter(scenario=scenario)]


def save(tenant, scenario, policies):
    if not isinstance(policies, list) or len(policies) > 100:
        raise ValidationError({"definition": t("scenarios.invalid_definition")})
    selected = {agent for trigger in scenario.definition["triggers"] if trigger["kind"] == "ai" for agent in trigger.get("agents", [])}
    lock_organization(tenant.organization_id)
    current = {grant.agent_id: grant for grant in AgentActionGrant.objects.select_for_update().filter(scenario=scenario)}
    seen = set()
    for policy in policies:
        if (not isinstance(policy, dict) or set(policy) != {"agent", "mode", "revision"}
                or type(policy["agent"]) is not int or policy["agent"] in seen
                or not isinstance(policy["mode"], str) or policy["mode"] not in {"off", "self", "ask"} or type(policy["revision"]) is not int):
            raise ValidationError({"definition": t("scenarios.invalid_definition")})
        seen.add(policy["agent"])
        grant = current.get(policy["agent"])
        if policy["revision"] != (grant.revision if grant else 0):
            from chatballs.integrations.scenarios.services import RevisionConflict
            raise RevisionConflict
        mode = policy["mode"] if policy["agent"] in selected else "off"
        if policy["agent"] not in selected and grant is None:
            raise ValidationError({"definition": t("scenarios.invalid_reference")})
        if grant is None:
            grant = AgentActionGrant(organization_id=tenant.organization_id, agent_id=policy["agent"], scenario=scenario)
        elif grant.mode == mode:
            continue
        else:
            grant.revision += 1
        from chatballs.integrations.execution.native_principal import capture_delegate
        capture_delegate(tenant, grant, mode)
        grant.mode = mode
        grant.save()
    for agent, grant in current.items():
        if agent not in selected and grant.mode != "off":
            grant.mode = "off"
            grant.revision += 1
            grant.save()
