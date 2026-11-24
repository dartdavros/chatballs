"""Clear the old executor scope after the demo transaction publishes its result."""

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.identity.demo_seed.north_wind.executor_scope import EXECUTOR_URL, RESET_EVENT, scope_key
from chatballs.identity.demo_seed.north_wind.executor_transport import send_external
from chatballs.integrations.adapters.auth import OutboundRequest
from chatballs.integrations.adapters.contracts import Limits
from chatballs.integrations.adapters.transport import TransportError
from chatballs.tenancy.context import TenantContext


def executor_reset_scope(dataset):
    binding = dataset.shop_state.get("externalExecutor")
    return {"connectionId": binding["connectionId"], "generation": str(dataset.generation)} if binding else None


def enqueue_executor_reset(context, scope):
    if scope:
        enqueue_event(DomainEvent(
            aggregate_type="DemoExternalExecutor", aggregate_id=scope["generation"],
            event_type=RESET_EVENT, payload=scope,
            tenant_context=TenantContext.for_resource(context.organization),
        ))


def run_executor_reset(context, scope):
    token = scope_key(context.organization_id, scope["generation"], scope["connectionId"])
    request = OutboundRequest("POST", EXECUTOR_URL + "/reset", headers={"Authorization": f"Bearer {token}"})
    response = send_external(request, limits=Limits(timeout_seconds=8, max_response_bytes=8192, max_file_bytes=8192))
    if response.status != 204:
        raise TransportError("executor_reset_failed")
