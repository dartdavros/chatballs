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
  failed,
  openChannel,
}: {
  channels: Channel[];
  failed: boolean;
  openChannel: (channelId: number) => void;
}) {
  // Архивный канал не принимает диалоги — в срезе отдела он не показывается.
  const active = channels.filter((channel) => channel.isActive);

  return (
    <div className="department-channels">
      <span className="department-channels-title">Каналы отдела</span>
      {failed ? (
        <p className="department-channels-empty">Не удалось загрузить каналы.</p>
      ) : active.length === 0 ? (
        <p className="department-channels-empty">Каналов нет.</p>
      ) : (
        <ul>
          {active.map((channel) => (
            <li key={channel.id}>
              <button className="link" type="button" onClick={() => openChannel(channel.id)}>
                {channel.name}
              </button>
              <em>{channel.counters.openConversations} открытых</em>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
