import { useState } from "react";

import { ChannelRow } from "./ChannelRow";
import type { Channel } from "./types";

export function ChannelsTable({
  channels,
  canManageLifecycle,
  canOpenAgent,
  openChannel,
  openAgent,
  requestToggleActive,
  onDelete,
  footer,
}: {
  channels: Channel[];
  canManageLifecycle: boolean;
  canOpenAgent: (channel: Channel) => boolean;
  openChannel: (channelId: number) => void;
  openAgent: (agentId: number) => void;
  requestToggleActive: (channel: Channel) => void;
  onDelete: (channel: Channel) => void;
  footer: string;
}) {
  const [menuId, setMenuId] = useState<number | null>(null);

  return (
    <div className="table-card channels-table-card">
      <table className="baseline-table channels-table">
        <thead>
          <tr>
            <th>КАНАЛ</th>
            <th>ПРОДУКТ</th>
            <th>ПОДКЛЮЧЕНИЯ</th>
            <th>AI-АГЕНТ</th>
            <th className="numeric">ДИАЛОГИ</th>
            <th aria-label="Действия" />
          </tr>
        </thead>
        <tbody>
          {channels.map((channel) => (
            <ChannelRow
              key={channel.id}
              channel={channel}
              canManageLifecycle={canManageLifecycle}
              canOpenAgent={canOpenAgent(channel)}
              menuId={menuId}
              setMenuId={setMenuId}
              openChannel={openChannel}
              openAgent={openAgent}
              requestToggleActive={requestToggleActive}
              onDelete={onDelete}
            />
          ))}
        </tbody>
      </table>
      <div className="channels-table-footer">
        <span>{footer}</span>
        <span>Счётчик «Диалоги» — открытые диалоги канала</span>
      </div>
    </div>
  );
}
