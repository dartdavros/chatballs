"""Register scoped demo tools and the approved order template with seeded agents."""

from chatballs.ai.skill_templates.order_basis import order_basis
from chatballs.ai.skills_models import AgentSkill
from chatballs.ai.tool_models import AgentTool
from chatballs.identity.demo_seed.north_wind.history_skills import create_history_skill
from chatballs.identity.demo_seed.north_wind.local_access import (
    issue_local_read_token,
    local_demo_enabled,
)
from chatballs.identity.demo_seed.north_wind.local_transport import HTTP_ORDER_URL, MCP_URL
from chatballs.integrations import mcp_client
from chatballs.integrations.external_headers import dump_secret_headers
from chatballs.integrations.models import Integration

_ORDER_PARAMETER = {"type": "integer", "minimum": 1}
_SIZE = {"type": "string", "enum": ["M", "L", "XL"], "default": "L"}
_REQUIRED_TOOLS = {"search_products", "get_product", "get_order_status"}


def load_local_tools(refs):
    if not refs.recorder:
        return
    dataset = refs.recorder.dataset
    language = refs.language
    skill = create_history_skill(refs, order_basis(language=language))
    refs.order_skill = skill
    if not local_demo_enabled():
        for agent_key in ("consultant", "support"):
            AgentSkill.objects.create(organization_id=dataset.organization_id, agent=refs.agents[agent_key], skill=skill)
        return
    verify_mock_service(dataset)
    for agent_key, customer in (("consultant", "andrey"), ("support", "andrey-after-purchase")):
        bind_order_tools(dataset, refs.agents[agent_key], customer, skill)
    dataset.shop_state["localTools"] = True
    dataset.save(update_fields=["shop_state"])


def bind_order_tools(dataset, agent, customer, skill):
    token = issue_local_read_token(dataset, customer=customer)
    mcp = _mcp(dataset, token, agent.channel.name)
    http = _http(dataset, token, agent.channel.name)
    for tool in mcp.tools:
        AgentTool.objects.create(organization_id=dataset.organization_id, agent=agent,
                                 integration=mcp, tool_name=tool["name"])
    AgentTool.objects.create(organization_id=dataset.organization_id, agent=agent, integration=http)
    AgentSkill.objects.create(organization_id=dataset.organization_id, agent=agent, skill=skill)


def verify_mock_service(dataset):
    token = issue_local_read_token(dataset, customer="andrey")
    try:
        tools = mcp_client.list_tools(MCP_URL, headers={"Authorization": f"Bearer {token}"}, timeout=5)
    except mcp_client.McpError:
        raise RuntimeError("The local North Wind MCP service is unavailable") from None
    observed = {
        tool.get("name") for tool in tools
        if isinstance(tool.get("annotations"), dict) and tool["annotations"].get("readOnlyHint") is True
    }
    if not _REQUIRED_TOOLS <= observed:
        raise RuntimeError("The local North Wind MCP service is missing required read-only tools")


def register_local_tool(dataset, token, **fields):
    config = fields.pop("config")
    return Integration.objects.create(
        organization_id=dataset.organization_id, kind="EXTERNAL_SERVER", status="UNCHECKED",
        config={**config, "headers": [{"name": "Authorization", "secret": True}]},
        secret_headers=dump_secret_headers({"Authorization": f"Bearer {token}"}),
        **fields,
    )


def _mcp(dataset, token, agent_name):
    tools = [
        _tool("search_products", "Подбор костюма и проверка каталога. Search ski clothing.", {
            "query": {"type": "string"}, "size": _SIZE, "budget": {"type": "integer"},
        }),
        _tool("get_product", "Цена и остатки модели. Read price and stock.", {
            "product_id": {"type": "string"}, "size": _SIZE,
        }, ["product_id"]),
        _tool("get_order_status", "Состав и текущий заказ. Read order details.", {
            "order_number": _ORDER_PARAMETER,
        }, ["order_number"]),
    ]
    return register_local_tool(
        dataset, token, provider="MCP", name=f"{agent_name} · MCP",
        config={"url": MCP_URL, "description": "Demo catalogue and orders"}, tools=tools,
    )


def _tool(name, description, properties, required=None):
    return {
        "name": name, "title": name, "description": description,
        "input_schema": {"type": "object", "properties": properties, "required": required or []},
        "read_only_hint": True,
    }


def _http(dataset, token, agent_name):
    return register_local_tool(
        dataset, token, provider="HTTP", name=f"{agent_name} · HTTP",
        config={
            "url": HTTP_ORDER_URL, "method": "POST", "read_only": True,
            "tool_name": "north_wind_delivery_status",
            "description": "Статус выдачи и доставки заказа. Read shipment status.",
            "parameters": [{
                "name": "order_number", "type": "number", "source": {"type": "ai"},
                "location": "body", "required": True,
            }],
        },
    )
