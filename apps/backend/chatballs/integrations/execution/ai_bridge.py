"""Bounded tools expose only explicit grants, with server-bound tenant/context."""

import json
import uuid
from dataclasses import dataclass, replace

from chatballs.ai.execution_version import configuration_version
from chatballs.ai.provider.base import ToolSpec
from chatballs.ai.tool_support import cached_tool_support
from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.ai_launch import launch_ai
from chatballs.integrations.execution.ai_policy import authorize_ai, bind, current
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.types import read_type
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.lookup import load_organization


def schema(spec):
    kind = {"date": "string", "datetime": "string", "lookup": "string", "file": "object"}.get(spec.type, spec.type)
    result = {} if kind == "enum" else {"type": kind}
    if spec.title_key or spec.hint_key:
        from chatballs.i18n import t
        result["description"] = " ".join(t(key) for key in (spec.title_key, spec.hint_key) if key)
    for attr, keyword in (("min_items", "minItems"), ("max_items", "maxItems"), ("max_length", "maxLength")):
        if getattr(spec, attr) is not None:
            result[keyword] = getattr(spec, attr)
    if spec.pattern:
        result["pattern"] = spec.pattern
    if spec.type == "lookup":
        result["type"] = ["string", "integer"]
    if spec.type == "object":
        result.update(properties={key: schema(child) for key, child in spec.properties},
                      required=[key for key, child in spec.properties if child.required], additionalProperties=spec.open)
    if spec.items:
        result["items"] = schema(spec.items)
    if spec.options:
        result["enum"] = [option.value for option in spec.options]
    if spec.type in {"date", "datetime"}:
        result["format"] = "date" if spec.type == "date" else "date-time"
    if spec.type == "file":
        result.update(properties={"fileId": {"type": "string", "format": "uuid"}}, required=["fileId"], additionalProperties=False)
    if spec.nullable:
        if "type" in result:
            result["type"] = ([*result["type"], "null"] if isinstance(result["type"], list) else [kind, "null"])
        elif None not in result.get("enum", []):
            result["enum"].append(None)
    return result


@dataclass(frozen=True)
class AgentActionTool:
    spec: ToolSpec
    title: str
    organization_id: int
    binding: dict
    status: bool = False
    preview: bool = False

    def execute(self, arguments, call_id):
        if not isinstance(arguments, dict):
            raise ExecutionDenied("arguments")
        tenant = TenantContext.for_resource(load_organization(self.organization_id))
        if not self.status:
            result = launch_ai(tenant, self.binding, arguments, f"{self.binding['turn']}:{call_id}", preview=self.preview)
            if self.preview:
                return json.dumps({"state": "not_executed", "arguments": result["arguments"],
                    "inputSchema": result["inputSchema"], "title": self.title}, ensure_ascii=False)
            return json.dumps({"runId": str(result.public_id), "state": result.state, "title": self.title})
        with tenant_atomic(tenant):
            if set(arguments) != {"runId"}:
                raise ExecutionDenied("arguments")
            try:
                public_id = uuid.UUID(arguments["runId"])
            except (ValueError, TypeError, AttributeError):
                raise ExecutionDenied("arguments") from None
            run = ScenarioRun.objects.filter(organization_id=tenant.organization_id,
                public_id=public_id, conversation_id=self.binding["conversation"]).first()
            if run is None or run.data_cleared_at or run.definition.get("ai", {}).get("agent") != self.binding["agent"]:
                raise ExecutionDenied("permission")
            if run.definition["ai"].get("tester") != self.binding.get("tester"):
                raise ExecutionDenied("permission")
            authorize_ai(tenant, run)
            from chatballs.integrations.execution.payloads import run_payload
            payload = run_payload(run, detail=True)
            return json.dumps({"runId": str(run.public_id), "state": run.state,
                               "steps": [{"state": step["state"], "arguments": step["arguments"], "result": step["result"]} for step in payload["steps"]]}, ensure_ascii=False)


def plan_actions(agent, conversation, *, preview=False, registry=None, test_tenant=None, test_client=None, turn_id=None, reserved_names=(), site_event_launch_id=None):
    if conversation is None and test_tenant is None or cached_tool_support(agent) is False:
        return []
    tenant = TenantContext.for_resource(agent.organization)
    tools = []
    names = set(reserved_names)
    def tool_name(base):
        name, suffix = base, 1
        while name in names:
            suffix += 1
            name = f"{base}_{suffix}"
        names.add(name)
        return name
    turn_id = str(turn_id or uuid.uuid4())
    for grant in AgentActionGrant.objects.filter(agent=agent, organization_id=agent.organization_id).exclude(
        mode="off").select_related("scenario", "integration", "agent"):
        binding = bind(grant, conversation) if conversation else {
            "grant": grant.pk, "agent": agent.pk, "revision": grant.revision, "mode": grant.mode,
            "delegate": grant.delegate_id,
            "tester": test_tenant.membership_id, "conversation": None,
            "modeVersion": test_tenant.organization.operation_mode_version}
        if not conversation and test_client:
            binding["testContext"] = {"contact": {key: getattr(test_client, key) for key in ("name", "email", "phone")}}
        binding["turn"] = turn_id
        binding["agentVersion"] = configuration_version(agent)
        if site_event_launch_id is not None:
            binding["siteEventLaunchId"] = site_event_launch_id
        try:
            current(tenant, binding)
            if grant.scenario_id:
                spec = read_type(grant.scenario.definition["parameters"])
                title = grant.scenario.name
            else:
                _, _, _, _, operation = resolve_action(agent.organization_id,
                    "chatballs" if grant.native_key else grant.integration_id,
                    f"chatballs:{grant.native_key}" if grant.native_key else f"service:{grant.operation_key}", registry=registry)
                spec = operation.input
                if grant.native_key and conversation:
                    spec = replace(spec, properties=tuple((name, child) for name, child in spec.properties
                        if name != "conversation_id" or not child.required))
                from chatballs.i18n import t
                title = t(operation.title_key)
            tools.append(AgentActionTool(ToolSpec(name=tool_name(f"chatballs_action_{grant.pk}"),
                description=title, parameters=schema(spec)), title, agent.organization_id, binding, preview=preview))
        except (ExecutionDenied, ValueError):
            continue
    if tools:
        tools.append(AgentActionTool(ToolSpec(name=tool_name("chatballs_action_status"),
            description="Read the actual state of an action launched in this conversation.", parameters={
                "type": "object", "properties": {"runId": {"type": "string"}}, "required": ["runId"],
                "additionalProperties": False}), "chatballs_action_status", agent.organization_id, tools[0].binding, status=True))
    return tools
