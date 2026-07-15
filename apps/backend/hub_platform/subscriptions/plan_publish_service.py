from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from hub_platform.subscriptions.keys import PlanCode
from hub_platform.subscriptions.models import PlanVersion
from hub_platform.subscriptions.plan_service import publish_plan_version

# Only saleable plans with fully approved grants are published by the canonical
# command. Business/Corporation stay draft until their features ship (C11/C12).
PUBLISHABLE_PLAN_CODES = (PlanCode.FREE, PlanCode.STARTUP)


@dataclass(frozen=True)
class PublishResult:
    plan_code: str
    published: bool
    already_published: bool
    public_id: str


@transaction.atomic
def publish_saleable_plan_versions() -> list[PublishResult]:
    """Publish the current (version=1) draft for each saleable plan whose grants
    are complete. Idempotent: an already-published version is reported as such
    without error. Raises if a publishable plan version is missing grants."""
    results: list[PublishResult] = []
    for code in PUBLISHABLE_PLAN_CODES:
        version = PlanVersion.objects.select_related("plan").get(
            plan__code=code, version=1
        )
        already = version.published_at is not None
        if not already:
            publish_plan_version(version)
            version.refresh_from_db()
        results.append(
            PublishResult(
                plan_code=code,
                published=not already,
                already_published=already,
                public_id=str(version.public_id),
            )
        )
    return results
