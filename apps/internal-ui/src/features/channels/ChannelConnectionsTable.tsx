import { StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { ChannelBadge, providerLabel } from "./ChannelBadge";
import { connectionStatus } from "./model";
import type { Channel } from "./types";

export function ChannelConnectionsTable({ channel, canManage, busy, onUnbind }: { channel: Channel; canManage: boolean; busy: boolean; onUnbind: (connectionId: number) => void }) {
  if (channel.connections.length === 0) return <p className="channel-muted">Подключений нет.</p>;
  return (
    <table className="baseline-table channel-connections-table">
      <thead><tr><th>ПОДКЛЮЧЕНИЕ</th><th>ПРОВАЙДЕР</th><th>СТАТУС</th><th aria-label="Действия" /></tr></thead>
      <tbody>
        {channel.connections.map((connection) => (
          <tr key={connection.id}>
            <td><strong>{connection.name}</strong><div className="channel-sub">{providerLabel(connection.provider)}</div></td>
            <td><ChannelBadge provider={connection.provider} /></td>
            <td><StatusPill status={connectionStatus(connection.status)} /></td>
            <td className="row-actions">{canManage && <Button variant="secondary" disabled={busy} onClick={() => onUnbind(connection.id)}>Отвязать</Button>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
