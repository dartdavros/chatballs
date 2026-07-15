from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import HumanUser
from hub_platform.subscriptions.models import (
    EntitlementDefinition,
    OverrideOperation,
    OverrideTarget,
    QuotaDefinition,
    SubscriptionOverride,
)
from hub_platform.tenancy.context import TenantContext


@transaction.atomic
def create_override(
    *,
    context: TenantContext,
    created_by: HumanUser,
    target: str,
    key: str,
    operation: str,
    reason: str,
    value: int | None = None,
    starts_at=None,
    ends_at=None,
) -> SubscriptionOverride:
    if not reason.strip():
        raise ValidationError({"reason": "Override reason is required"})
    fields: dict[str, object] = {}
    if target == OverrideTarget.ENTITLEMENT:
        fields["entitlement_definition"] = EntitlementDefinition.objects.get(key=key)
        if operation not in {OverrideOperation.ENABLE, OverrideOperation.DISABLE}:
            raise ValidationError({"operation": "Invalid entitlement override operation"})
    elif target == OverrideTarget.QUOTA:
        fields["quota_definition"] = QuotaDefinition.objects.get(key=key)
        if operation not in {OverrideOperation.SET, OverrideOperation.ADD}:
            raise ValidationError({"operation": "Invalid quota override operation"})
    else:
        raise ValidationError({"target": "Invalid override target"})
    override = SubscriptionOverride(
        organization=context.organization,
        target=target,
        operation=operation,
        value=value,
        reason=reason.strip(),
        starts_at=starts_at or timezone.now(),
        ends_at=ends_at,
        created_by=created_by,
        correlation_id=context.correlation_id,
        **fields,
    )
    override.full_clean()
    override.save()
    record_audit_event(
        action="subscription.override_created",
        actor=created_by,
        organization=context.organization,
        object_type="SubscriptionOverride",
        object_id=str(override.id),
        payload={
            "target": target,
            "key": key,
            "operation": operation,
            "value": value,
            "reason": reason.strip(),
            "endsAt": ends_at.isoformat() if ends_at else None,
        },
    )
    return override
