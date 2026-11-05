"""Outbox contains identity only; operational values remain encrypted once."""

from django.db import transaction

from chatballs.conversations.realtime import conversation_group, inbox_group
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.integrations.scenario_state.journal import RunJournalEntry
from chatballs.realtime import publish
from chatballs.tenancy.context import TenantActorKind, TenantContext


def system_context(tenant):
    # Revoked human membership must not strand already-sent effects in outbox.
    return TenantContext.for_resource(tenant.organization, actor_kind=TenantActorKind.SYSTEM,
                                      correlation_id=tenant.correlation_id)


def schedule(tenant, run, *, at=None):
    enqueue_event(DomainEvent(aggregate_type="scenario_run", aggregate_id=str(run.public_id),
                             event_type="integrations.run", payload={"runId": str(run.public_id)},
                             tenant_context=system_context(tenant)), available_at=at)


def journal(run, code, step=None):
    RunJournalEntry.objects.create(organization_id=run.organization_id, run=run, code=code,
                                  path=step.path if step else "", attempt=step.attempt if step else 0)
    organization_id, conversation_id = run.organization_id, run.conversation_id
    def changed():
        # Identifier-free invalidation uses the existing scoped subscriptions.
        publish(inbox_group(organization_id), {"type": "service_runs.changed"})
        if conversation_id:
            publish(conversation_group(conversation_id), {"type": "service_runs.changed"})
    transaction.on_commit(changed)
