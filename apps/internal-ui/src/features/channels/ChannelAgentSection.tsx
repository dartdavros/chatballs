import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { agentStatus } from "./model";
import type { Channel } from "./types";

/** Одна строка сводки и переход наружу: редактор агента остаётся на его странице. */
export function ChannelAgentSection({
  channel,
  canOpenAgent,
  openAgent,
  openAgentCreate,
}: {
  channel: Channel;
  canOpenAgent: boolean;
  openAgent: (agentId: number) => void;
  openAgentCreate: () => void;
}) {
  return (
    <section className="channel-card-section channel-agent-section">
      <div className="channel-section-eyebrow">AI-АГЕНТ</div>
      {channel.agent ? (
        <div className="channel-agent-row">
          <span className="channel-agent-mark"><Icon name="robot" size={18} /></span>
          <div className="channel-agent-summary">
            <b>{channel.agent.name}</b>
            <span>·</span>
            <StatusPill status={agentStatus(channel.agent.status)} />
            <span>·</span>
            <code>{channel.agent.model}</code>
          </div>
          {canOpenAgent && (
            <button className="link has-icon" type="button" onClick={() => openAgent(channel.agent!.id)}>
              Открыть агента
              <Icon name="arrow" size={14} />
            </button>
          )}
        </div>
      ) : (
        <div className="channel-agent-none">
          <span className="channel-agent-mark"><Icon name="robot" size={22} /></span>
          <strong>Агента нет, канал ведут операторы</strong>
          <p>Это рабочее состояние. При создании AI-агента нужный канал выбирается в разделе AI.</p>
          {canOpenAgent && (
            <button className="link has-icon" type="button" onClick={openAgentCreate}>
              Создать агента в разделе AI
              <Icon name="arrow" size={14} />
            </button>
          )}
        </div>
      )}
    </section>
  );
}
