from dataclasses import dataclass

from hub_platform.channels.models import Channel


@dataclass(frozen=True)
class ChannelInput:
    name: str


def update_channel(*, channel: Channel, data: ChannelInput) -> Channel:
    # Минимум: переименование канала. code/model/флаги политики не трогаем —
    # смена code сломала бы embed-сниппеты (data-channel) и URL.
    channel.name = data.name
    channel.save(update_fields=["name", "updated_at"])
    return channel
