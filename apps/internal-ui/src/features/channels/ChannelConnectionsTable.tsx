import { ChannelBadge } from "../../shared/badges";
import { providerLabel } from "../../shared/providers";
import { StatusPill } from "../../shared/ui";
import { connectionStatus } from "./model";
import type { Channel } from "./types";

export function ChannelConnectionsTable({ channel }: { channel: Channel }) {
  if (channel.connections.length === 0) return <p className="channel-muted">Подключений нет.</p>;
  return (
    <div className="channel-connections">
      {channel.connections.map((connection) => (
        <div className="channel-connection" key={connection.id}>
          <ChannelBadge provider={connection.provider} />
          <div className="channel-connection-text"><strong>{connection.name}</strong><span>{providerLabel(connection.provider)}</span></div>
          <StatusPill status={connectionStatus(connection.status)} />
        </div>
      ))}
    </div>
  );
}
