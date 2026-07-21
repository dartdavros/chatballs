import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { ChannelBadge, providerLabel } from "./ChannelBadge";
import { ChannelWizardSummary } from "./ChannelWizardSummary";
import type { Channel } from "./types";

export type WizardIntegration = { id: number; provider: string; name: string };

export function ChannelWizardConnectionsStep({
  channel,
  integrations,
  loadingFailed,
  connectionError,
  busyId,
  onBind,
  openChannel,
  openChannels,
  openAgentCreate,
}: {
  channel: Channel;
  integrations: WizardIntegration[];
  loadingFailed: boolean;
  connectionError: string | null;
  busyId: number | null;
  onBind: (integrationId: number) => void;
  openChannel: (channelId: number) => void;
  openChannels: () => void;
  openAgentCreate: () => void;
}) {
  return (
    <div className="channel-wizard-final">
      <div className="channel-wizard-main">
        <section className="channel-card-section">
          <header><h3>Подключения</h3><span>Шаг можно пропустить</span></header>
          {loadingFailed ? <p className="channel-feedback is-error">Не удалось загрузить подключения.</p> : integrations.length === 0 ? (
            <p className="channel-muted">Свободных подключений нет — их можно привязать позже в карточке канала.</p>
          ) : (
            <div className="channel-connections">
              {integrations.map((integration) => {
                const bound = channel.connections.some((item) => item.id === integration.id);
                return (
                  <div className="channel-connection" key={integration.id}>
                    <ChannelBadge provider={integration.provider} />
                    <div className="channel-connection-text"><strong>{integration.name}</strong><span>{providerLabel(integration.provider)}</span></div>
                    <Button variant="secondary" disabled={bound || busyId !== null} onClick={() => onBind(integration.id)}>{bound ? "Привязано" : "Привязать"}</Button>
                  </div>
                );
              })}
            </div>
          )}
          {connectionError && <div className="channel-feedback is-error">{connectionError}</div>}
        </section>
        <section className="channel-card-section channel-wizard-done">
          <span className="channel-wizard-check"><Icon name="check" size={28} /></span>
          <strong>Канал создан</strong>
          <p><b>{channel.name}</b> — операторский канал: AI-агента нет, диалоги ведут операторы. Канал готов к привязке подключений и приёму диалогов.</p>
          <div className="channel-wizard-actions is-centered">
            <Button variant="primary" onClick={() => openChannel(channel.id)}>Открыть карточку канала</Button>
            <Button variant="secondary" onClick={openChannels}>К списку каналов</Button>
          </div>
        </section>
      </div>
      <ChannelWizardSummary channel={channel} openAgentCreate={openAgentCreate} />
    </div>
  );
}
