import { useEffect, useState } from "react";

import { ApiError, api } from "../../api/client";
import { Button } from "../../shared/ui-controls";
import { ChannelBadge, providerLabel } from "./ChannelBadge";
import { bindConnection, unbindConnection } from "./api";
import type { Channel } from "./types";

type Integration = {
  id: number;
  kind: string;
  provider: string;
  name: string;
  channelId: number | null;
};

type Transfer = { integration: Integration; fromChannel: string };

export function ChannelConnectionsSection({
  channel,
  canManage,
  onChanged,
}: {
  channel: Channel;
  canManage: boolean;
  onChanged: (channel: Channel) => void;
}) {
  const [picking, setPicking] = useState(false);
  const [available, setAvailable] = useState<Integration[]>([]);
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!picking) return;
    void api<{ items: Integration[] }>("/api/v1/integrations/")
      .then((response) =>
        setAvailable(
          response.items.filter(
            (item) => item.kind === "MESSENGER" && item.channelId !== channel.id,
          ),
        ),
      )
      .catch(() => setAvailable([]));
  }, [picking, channel.id]);

  async function bind(integration: Integration, force = false) {
    setError(null);
    try {
      const response = await bindConnection(channel.id, integration.id, force);
      onChanged(response.channel);
      setPicking(false);
      setTransfer(null);
    } catch (bindError) {
      if (bindError instanceof ApiError) {
        const payload = bindError.payload as {
          code?: string;
          currentChannel?: { id: number; name: string };
        };
        // Подключение принадлежит ровно одному каналу: перенос требует явного
        // подтверждения и пишется в аудит (ADR-HUB-0019, §6.6).
        if (payload.code === "connection_already_bound" && payload.currentChannel) {
          setTransfer({ integration, fromChannel: payload.currentChannel.name });
          return;
        }
        setError(bindError.message);
      }
    }
  }

  return (
    <section className="channel-card-section">
      <header>
        <h3>Подключения</h3>
        {canManage && channel.isActive && (
          <Button variant="secondary" icon="plus" onClick={() => setPicking(!picking)}>
            Привязать подключение
          </Button>
        )}
      </header>

      {!channel.isActive && (
        <p className="channel-muted">
          Архивный канал не выбирается при привязке подключения.
        </p>
      )}
      {error && <div className="channel-feedback is-error">{error}</div>}

      {channel.connections.length === 0 ? (
        <p className="channel-muted">Подключений нет.</p>
      ) : (
        <div className="channel-connections">
          {channel.connections.map((connection) => (
            <div className="channel-connection" key={connection.id}>
              <ChannelBadge provider={connection.provider} />
              <div className="channel-connection-text">
                <strong>{connection.name}</strong>
                <span>{providerLabel(connection.provider)}</span>
              </div>
              <span className={`channel-status channel-status--${connection.status.toLowerCase()}`}>
                <i />
                {connection.status}
              </span>
              {canManage && (
                <Button
                  variant="secondary"
                  onClick={async () => {
                    const response = await unbindConnection(channel.id, connection.id);
                    onChanged(response.channel);
                  }}
                >
                  Отвязать
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {picking && (
        <div className="channel-connection-picker">
          <span className="channel-section-eyebrow">СВОБОДНЫЕ И ЧУЖИЕ ПОДКЛЮЧЕНИЯ</span>
          {available.length === 0 ? (
            <p className="channel-muted">Подключений нет. Создайте их в разделе «Интеграции».</p>
          ) : (
            available.map((integration) => (
              <div className="channel-connection" key={integration.id}>
                <ChannelBadge provider={integration.provider} />
                <div className="channel-connection-text">
                  <strong>{integration.name}</strong>
                  <span>
                    {providerLabel(integration.provider)}
                    {integration.channelId !== null && " · привязано к другому каналу"}
                  </span>
                </div>
                <Button variant="secondary" onClick={() => bind(integration)}>
                  Привязать
                </Button>
              </div>
            ))
          )}
        </div>
      )}

      {transfer && (
        <div className="channel-modal-backdrop" role="dialog">
          <div className="channel-modal">
            <div className="channel-modal-head">
              <strong>Перенести подключение в этот канал?</strong>
              <p>
                Подключение <b>«{transfer.integration.name}»</b> уже привязано к каналу{" "}
                <b>«{transfer.fromChannel}»</b>. Подключение принадлежит ровно одному каналу —
                перенос отвяжет его от прежнего.
              </p>
            </div>
            <div className="channel-modal-body">
              <div className="channel-transfer-path">
                <ChannelBadge provider={transfer.integration.provider} />
                <span>{transfer.fromChannel}</span>
                <i>→</i>
                <b>{channel.name}</b>
              </div>
              <p className="channel-muted">
                Существующие диалоги остаются в прежнем канале. Действие пишется в аудит как
                перенос.
              </p>
            </div>
            <div className="channel-modal-actions">
              <Button variant="secondary" onClick={() => setTransfer(null)}>
                Отмена
              </Button>
              <Button variant="primary" onClick={() => bind(transfer.integration, true)}>
                Перенести подключение
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
