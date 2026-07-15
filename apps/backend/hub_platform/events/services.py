from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from hub_platform.events.context import get_correlation_id
from hub_platform.events.models import EventOwnership, OutboxEvent, OutboxStatus
from hub_platform.identity.models import Organization, OrganizationMembership
from hub_platform.tenancy.context import TenantActorKind, TenantContext


@dataclass(frozen=True)
class DomainEvent:
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict[str, Any]
    tenant_context: TenantContext | None = None


def enqueue_event(event: DomainEvent) -> OutboxEvent:
    context = event.tenant_context
    return OutboxEvent.objects.create(
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        event_type=event.event_type,
        payload=event.payload,
        ownership=EventOwnership.TENANT if context is not None else EventOwnership.PLATFORM,
        organization=context.organization if context is not None else None,
        membership=context.membership if context is not None else None,
        actor_user=context.actor_user if context is not None else None,
        actor_kind=context.actor_kind if context is not None else "",
        correlation_id=context.correlation_id if context is not None else get_correlation_id(),
    )


def tenant_context_for_event(event: OutboxEvent) -> TenantContext | None:
    if event.ownership == EventOwnership.PLATFORM:
        if event.organization_id or event.membership_id:
            raise ValueError("Platform event cannot carry tenant ownership")
        return None
    if event.organization_id is None:
        raise ValueError("Tenant event has no organization")
    organization = Organization.objects.get(pk=event.organization_id)
    try:
        actor_kind = TenantActorKind(event.actor_kind)
    except ValueError as error:
        raise ValueError("Tenant event has invalid actor kind") from error
    resource_context = TenantContext.for_resource(
        organization,
        actor_kind=actor_kind,
        correlation_id=event.correlation_id,
    )
    from hub_platform.tenancy.database import tenant_atomic

    with tenant_atomic(resource_context):
        membership = None
        actor_user = None
        if event.membership_id is not None:
            membership = OrganizationMembership.objects.select_related(
                "user", "organization"
            ).get(
                pk=event.membership_id,
                organization=organization,
                blocked_at__isnull=True,
                user__is_active=True,
            )
            actor_user = membership.user
            if event.actor_user_id not in {None, membership.user_id}:
                raise ValueError("Tenant event actor does not match membership")
        elif event.actor_user_id is not None:
            actor_user = event.actor_user
        if actor_kind == TenantActorKind.HUMAN and membership is None:
            raise ValueError("Human tenant event has no membership")
        return TenantContext(
            organization=organization,
            membership=membership,
            actor_user=actor_user,
            actor_kind=actor_kind,
            correlation_id=event.correlation_id,
        )


def mark_retry(event: OutboxEvent, error: str, max_attempts: int = 5) -> None:
    event.attempts += 1
    event.last_error = error
    event.status = OutboxStatus.DEAD_LETTER if event.attempts >= max_attempts else OutboxStatus.FAILED
    event.next_attempt_at = timezone.now() + timedelta(seconds=min(300, 2**event.attempts))
    event.save(
        using="platform",
        update_fields=["attempts", "last_error", "status", "next_attempt_at"],
    )


def claim_next_outbox_event() -> OutboxEvent | None:
    with transaction.atomic(using="platform"):
        event = (
            OutboxEvent.objects.using("platform").select_for_update(skip_locked=True)
            .filter(
                status__in=[OutboxStatus.PENDING, OutboxStatus.FAILED],
                next_attempt_at__lte=timezone.now(),
            )
            .order_by("next_attempt_at", "created_at")
            .first()
        )
        if event is None:
            return None
        event.status = OutboxStatus.PROCESSING
        event.save(using="platform", update_fields=["status"])
        return event
