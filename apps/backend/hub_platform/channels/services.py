from dataclasses import dataclass

from hub_platform.channels.models import Channel
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True)
class ChannelInput:
    name: str


def update_channel(
    *, context: TenantContext, channel: Channel, data: ChannelInput
) -> Channel:
    if channel.organization_id != context.organization_id:
        raise ValueError("Channel belongs to another organization")
    # Минимум: переименование канала. code/model/флаги политики не трогаем —
    # смена code сломала бы embed-сниппеты (data-channel) и URL.
    channel.name = data.name
    channel.save(update_fields=["name", "updated_at"])
    return channel
