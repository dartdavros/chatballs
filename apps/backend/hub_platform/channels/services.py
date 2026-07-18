from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai.knowledge_conflicts import (
    require_channel_department_compatible,
)
from hub_platform.channels.models import Channel
from hub_platform.identity.models import Department, DepartmentStatus
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True)
class ChannelInput:
    name: str
    department_id: int | None


def _department_for_channel(
    *, context: TenantContext, department_id: int | None
) -> Department | None:
    if department_id is None:
        return None
    try:
        return Department.objects.get(
            id=department_id,
            organization_id=context.organization_id,
            status=DepartmentStatus.ACTIVE,
        )
    except Department.DoesNotExist as error:
        raise ValidationError({"departmentId": "Unknown or disabled department"}) from error


@transaction.atomic
def update_channel(*, context: TenantContext, channel: Channel, data: ChannelInput) -> Channel:
    if channel.organization_id != context.organization_id:
        raise ValidationError({"channel": "Channel belongs to another organization"})
    locked = Channel.objects.select_for_update().get(
        id=channel.id,
        organization_id=context.organization_id,
    )
    department = _department_for_channel(
        context=context,
        department_id=data.department_id,
    )
    if locked.department_id != data.department_id:
        require_channel_department_compatible(
            channel=locked,
            department_id=data.department_id,
        )
    # code/model/policy flags remain unchanged: code is part of embed URLs.
    locked.name = data.name
    locked.department = department
    locked.save(update_fields=["name", "department", "updated_at"])
    return locked
