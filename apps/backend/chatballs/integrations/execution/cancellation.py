"""Bounded wake-up of descendants; authorization stops effects immediately."""

from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.execution.events import schedule, system_context
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.lookup import load_organization


def schedule_children(run, after=0):
    if not run.children.filter(finished_at__isnull=True, pk__gt=after).exists():
        return
    tenant = TenantContext.for_resource(load_organization(run.organization_id))
    enqueue_event(DomainEvent(aggregate_type="scenario_cancel", aggregate_id=str(run.public_id),
        event_type="integrations.cancel_children", payload={"runId": str(run.public_id), "after": after},
        tenant_context=system_context(tenant)))


@register("integrations.cancel_children")
def wake_children(payload, tenant):
    run = ScenarioRun.objects.get(public_id=payload["runId"], organization_id=tenant.organization_id)
    children = list(run.children.filter(finished_at__isnull=True, pk__gt=payload["after"]).order_by("pk")[:50])
    for child in children:
        schedule(tenant, child)
    if len(children) == 50:
        schedule_children(run, children[-1].pk)
