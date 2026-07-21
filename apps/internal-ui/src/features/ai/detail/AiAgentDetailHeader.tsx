import { Icon } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import { productAccent } from "../../../shared/utils";
import { dailyBudget, type AiAgentDetail } from "./model";

export function AiAgentDetailHeader({ agent, onOpenChannel }: { agent: AiAgentDetail; onOpenChannel: () => void }) {
  const accent = productAccent(agent.channel.code);
  return (
    <section className="ai-agent-header">
      <div className="ai-agent-heading">
        <span className="ai-agent-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="robot" size={27} /></span>
        <div className="ai-agent-title">
          <div className="ai-agent-title-row">
            <h1>{agent.name}</h1>
            <StatusPill status={agent.isActive ? "active" : "disabled"} />
          </div>
          <div className="ai-agent-meta">
            <div><span>Канал</span><button type="button" className="link" onClick={onOpenChannel}>{agent.channel.name}</button></div>
            <div><span>Модель</span><code className="ai-mono">{agent.model}</code></div>
            <div><span>Знания</span><b>{agent.knowledge.length > 0 ? `${agent.knowledge.length} выбрано` : "—"}</b></div>
            <div><span>Лимиты</span><b>{dailyBudget(agent.limits)}</b></div>
          </div>
        </div>
      </div>
    </section>
  );
}
