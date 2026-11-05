"""Explicit agent policies share the human editor's atomic revision checks."""

from functools import partial

from chatballs.integrations.action_catalog.scenario_schemas import REVISION, field, named
from chatballs.integrations.action_catalog.scenarios import invoke
from chatballs.integrations.action_catalog.schema import action, enum, obj, required
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.execution import agent_policy_management

CHANNEL = field("channel", "integer", required=True)
MODE = required(named("mode", enum(("off", "self", "ask"), "native.scenario_mode")))
ITEM = obj(id=field("action", required=True), mode=MODE, revision=REVISION)
OUTPUT = obj(items=field("nativeActions", "array", items=obj(**dict(ITEM.properties),
    title=field("name"), subtitle=field("subtitle"), available=field("available", "boolean"), writes=field("writes", "boolean"))))


def update(tenant, data):
    return agent_policy_management.update(tenant, data["channel_id"], {"items": data["items"]})


for method, inputs, service, arguments, body in (
    ("GET", obj(channel_id=CHANNEL), agent_policy_management.listing, ("channel_id",), False),
    ("PUT", obj(channel_id=CHANNEL, items=field("agentPolicies", "array", items=ITEM, required=True, max_items=1000)), update, (), True),
):
    key = f"agents.actions.{method.lower()}"
    action(key=key, title=f"native.{key}", input=inputs, output=OUTPUT,
        handler=partial(invoke, service=service, arguments=arguments, body=body),
        capability="ai.manage", scope="organization", route="integrations/agent-actions/<int:channel_id>/",
        view="chatballs.integrations.execution.agent_actions.AgentActionsView", method=method,
        effect=Effect.READ if method == "GET" else Effect.UPDATE)
