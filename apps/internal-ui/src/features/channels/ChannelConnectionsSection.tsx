import { Icon } from "../../shared/icons";
import { ChannelConnectionsTable } from "./ChannelConnectionsTable";
import type { Channel } from "./types";

export function ChannelConnectionsSection({
  channel,
  canOpenIntegrations,
  openIntegrations,
}: {
  channel: Channel;
  canOpenIntegrations: boolean;
  openIntegrations: () => void;
}) {
  return (
    <section className="channel-card-section">
      <header>
        <h3>Подключения</h3>
        {canOpenIntegrations && (
          <button className="link has-icon" type="button" onClick={openIntegrations}>
            Открыть интеграции
            <Icon name="arrow" size={14} />
          </button>
        )}
      </header>
      <ChannelConnectionsTable channel={channel} />
    </section>
  );
}
