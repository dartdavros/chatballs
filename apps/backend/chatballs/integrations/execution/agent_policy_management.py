"""One permission-checked batch command for human and native policy editors."""

from chatballs.ai.models import AIAgent
from chatballs.integrations.execution.agent_actions import catalog, change_policy
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.service_connections.management_reads import require
from chatballs.tenancy.database import tenant_atomic


def agent(tenant, channel_id):
    require(tenant, "ai.manage")
    return AIAgent.objects.get(organization_id=tenant.organization_id, channel_id=channel_id)


def listing(tenant, channel_id):
    with tenant_atomic(tenant):
        rows = catalog(tenant.organization_id, agent(tenant, channel_id))
        return {"items": [{k: v for k, v in row.items()
            if k not in {"integration", "operation", "scenario", "native"}} for row in rows]}


def update(tenant, channel_id, data):
    with tenant_atomic(tenant):
        selected = agent(tenant, channel_id)
        if not isinstance(data, dict) or set(data) != {"items"} or not isinstance(data["items"], list) or len(data["items"]) > 1000:
            raise ExecutionDenied("arguments")
        seen = set()
        for item in data["items"]:
            if not isinstance(item, dict) or set(item) != {"id", "mode", "revision"} or not isinstance(item["id"], str) or item["id"] in seen:
                raise ExecutionDenied("arguments")
            seen.add(item["id"])
            change_policy(tenant, selected, item["id"], item["mode"], item["revision"])
        return listing(tenant, channel_id)
