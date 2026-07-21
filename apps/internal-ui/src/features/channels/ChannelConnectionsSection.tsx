import { useEffect, useState } from "react";

import { ApiError, api } from "../../api/client";
import { Button } from "../../shared/ui-controls";
import { bindConnection, unbindConnection } from "./api";
import { ChannelConnectionPicker } from "./ChannelConnectionPicker";
import { ChannelConnectionsTable } from "./ChannelConnectionsTable";
import { ChannelTransferDialog } from "./ChannelTransferDialog";
import type { ConnectionCandidate, ConnectionTransfer } from "./channel-connection-types";
import type { Channel } from "./types";

export function ChannelConnectionsSection({ channel, canManage, initiallyOpen = false, onChanged }: { channel: Channel; canManage: boolean; initiallyOpen?: boolean; onChanged: (channel: Channel) => void }) {
  const [picking, setPicking] = useState(initiallyOpen);
  const [available, setAvailable] = useState<ConnectionCandidate[]>([]);
  const [loadFailed, setLoadFailed] = useState(false);
  const [transfer, setTransfer] = useState<ConnectionTransfer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!picking) return;
    void api<{ items: ConnectionCandidate[] }>("/api/v1/integrations/")
      .then((response) => {
        setAvailable(response.items.filter((item) => item.kind === "MESSENGER" && item.channelId !== channel.id));
        setLoadFailed(false);
      })
      .catch(() => setLoadFailed(true));
  }, [picking, channel.id]);

  useEffect(() => {
    if (!initiallyOpen) return;
    document.getElementById("channel-connections")?.scrollIntoView({ block: "start" });
  }, [initiallyOpen]);

  async function bind(integration: ConnectionCandidate, force = false) {
    setError(null);
    setBusy(true);
    try {
      const response = await bindConnection(channel.id, integration.id, force);
      onChanged(response.channel);
      setPicking(false);
      setTransfer(null);
    } catch (bindError) {
      if (bindError instanceof ApiError) {
        const payload = bindError.payload as { code?: string; currentChannel?: { name: string } };
        if (payload.code === "connection_already_bound" && payload.currentChannel) setTransfer({ integration, fromChannel: payload.currentChannel.name });
        else setError(bindError.message);
      } else setError("Не удалось привязать подключение.");
    } finally {
      setBusy(false);
    }
  }

  async function unbind(connectionId: number) {
    setBusy(true);
    setError(null);
    try {
      const response = await unbindConnection(channel.id, connectionId);
      onChanged(response.channel);
    } catch (unbindError) {
      setError(unbindError instanceof ApiError ? unbindError.message : "Не удалось отвязать подключение.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="channel-card-section" id="channel-connections">
      <header><h3>Подключения</h3>{canManage && channel.isActive && <Button variant="secondary" icon="plus" onClick={() => setPicking((value) => !value)}>Привязать подключение</Button>}</header>
      {!channel.isActive && <p className="channel-muted">Архивный канал не выбирается при привязке подключения.</p>}
      {error && <div className="channel-feedback is-error">{error}</div>}
      <ChannelConnectionsTable channel={channel} canManage={canManage} busy={busy} onUnbind={(id) => void unbind(id)} />
      {picking && <ChannelConnectionPicker items={available} failed={loadFailed} busy={busy} onBind={(item) => void bind(item)} />}
      <ChannelTransferDialog transfer={transfer} channelName={channel.name} busy={busy} onConfirm={() => transfer && void bind(transfer.integration, true)} onClose={() => setTransfer(null)} />
    </section>
  );
}
