from typing import Any

from django.http import HttpRequest

from hub_platform.events.context import get_correlation_id
from hub_platform.identity.models import AuditEvent, AuditResult, HumanUser, Organization


def record_audit_event(
    *,
    action: str,
    result: str = AuditResult.SUCCESS,
    organization: Organization | None = None,
    actor: HumanUser | None = None,
    object_type: str = "",
    object_id: str = "",
    payload: dict[str, Any] | None = None,
    request: HttpRequest | None = None,
) -> AuditEvent:
    source_ip = None
    if request is not None:
        source_ip = request.META.get("REMOTE_ADDR")

    return AuditEvent.objects.create(
        organization=organization,
        actor=actor if actor and actor.is_authenticated else None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        result=result,
        payload=payload or {},
        correlation_id=get_correlation_id(),
        source_ip=source_ip,
    )
