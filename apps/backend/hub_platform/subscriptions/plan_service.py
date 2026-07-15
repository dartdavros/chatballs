from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import PlanVersion


@transaction.atomic
def publish_plan_version(plan_version: PlanVersion) -> PlanVersion:
    locked = PlanVersion.objects.select_for_update().get(pk=plan_version.pk)
    if locked.published_at is not None:
        return locked
    if not locked.entitlement_grants.exists() or not locked.quota_grants.filter(
        definition__key=QuotaKey.AI_AGENT_SLOTS
    ).exists():
        raise ValidationError("PlanVersion requires entitlement and quota grants before publish")
    locked.full_clean()
    locked.published_at = timezone.now()
    locked.save(update_fields=["published_at"])
    return locked
