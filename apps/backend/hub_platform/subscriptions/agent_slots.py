from __future__ import annotations

from django.db import transaction

from hub_platform.identity.audit import record_audit_event
from hub_platform.subscriptions.errors import InvalidAgentTransition, PolicyUnavailable
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import Subscription
from hub_platform.subscriptions.usage_service import record_usage
from hub_platform.tenancy.context import TenantContext


@transaction.atomic
def set_agent_status(*, context: TenantContext, agent_id: int, target_status: str):
    from hub_platform.ai.models import AIAgent, AIAgentStatus

    try:
        Subscription.objects.select_for_update().get(
            organization_id=context.organization_id
        )
    except Subscription.DoesNotExist as error:
        raise PolicyUnavailable("Organization has no subscription") from error
    agent = AIAgent.objects.select_for_update().get(
        pk=agent_id,
        organization_id=context.organization_id,
    )
    current_status = agent.status
    if current_status == target_status:
        return agent
    if current_status == AIAgentStatus.ARCHIVED:
        raise InvalidAgentTransition("Archived AI agent cannot change state")
    if target_status == AIAgentStatus.DRAFT:
        raise InvalidAgentTransition("AI agent cannot return to draft")
    if target_status not in AIAgentStatus.values:
        raise InvalidAgentTransition("Unknown AI agent state")

    transition_version = agent.lifecycle_version + 1
    if target_status == AIAgentStatus.ACTIVE:
        record_usage(
            context=context,
            quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=1,
            idempotency_key=f"ai-agent:{agent.id}:activate:{transition_version}",
            source="ai.agent_activation",
            aggregate_type="AIAgent",
            aggregate_id=str(agent.id),
        )
    elif current_status == AIAgentStatus.ACTIVE:
        record_usage(
            context=context,
            quota_key=QuotaKey.AI_AGENT_SLOTS,
            quantity=-1,
            idempotency_key=f"ai-agent:{agent.id}:release:{transition_version}",
            source="ai.agent_deactivation",
            aggregate_type="AIAgent",
            aggregate_id=str(agent.id),
        )

    agent.status = target_status
    agent.lifecycle_version = transition_version
    agent.save(update_fields=["status", "lifecycle_version", "updated_at"])
    record_audit_event(
        action="ai.agent_status_changed",
        actor=context.actor_user,
        organization=context.organization,
        object_type="AIAgent",
        object_id=str(agent.id),
        payload={"previous": current_status, "current": target_status},
    )
    return agent
