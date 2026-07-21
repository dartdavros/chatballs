import { Button } from "../../shared/ui-controls";
import { ChannelBadge, providerLabel } from "./ChannelBadge";
import type { ConnectionCandidate } from "./channel-connection-types";

export function ChannelConnectionPicker({ items, failed, busy, onBind }: { items: ConnectionCandidate[]; failed: boolean; busy: boolean; onBind: (integration: ConnectionCandidate) => void }) {
  return (
    <div className="channel-connection-picker">
      <span className="channel-section-eyebrow">ДОСТУПНЫЕ ПОДКЛЮЧЕНИЯ</span>
      {failed ? <p className="channel-feedback is-error">Не удалось загрузить подключения.</p> : items.length === 0 ? (
        <p className="channel-muted">Подключений нет. Создайте их в разделе «Интеграции».</p>
      ) : items.map((integration) => (
        <div className="channel-connection" key={integration.id}>
          <ChannelBadge provider={integration.provider} />
          <div className="channel-connection-text">
            <strong>{integration.name}</strong>
            <span>{providerLabel(integration.provider)}{integration.channelId !== null && " · используется другим каналом"}</span>
          </div>
          <Button variant="secondary" disabled={busy} onClick={() => onBind(integration)}>Привязать</Button>
        </div>
      ))}
    </div>
  );
}
