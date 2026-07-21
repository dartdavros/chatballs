import type { Channel } from "../channels/types";

/**
 * Read-only срез каналов отдела (SPEC-HUB-0027 §11.4).
 *
 * Отдел не владеет каналом: канал связывает отдел и продукт и не принадлежит
 * ни одному из них. Поэтому здесь только список и переход — создание и
 * изменение канала выполняется в разделе «Каналы».
 */
export function DepartmentChannels({
  channels,
  openChannel,
}: {
  channels: Channel[];
  openChannel: (channelId: number) => void;
}) {
  if (channels.length === 0) return null;
  return (
    <div className="department-channels">
      <span className="department-channels-title">Каналы отдела</span>
      <ul>
        {channels.map((channel) => (
          <li key={channel.id}>
            <button type="button" onClick={() => openChannel(channel.id)}>
              {channel.name}
            </button>
            <em>{channel.counters.openConversations} открытых</em>
          </li>
        ))}
      </ul>
    </div>
  );
}
