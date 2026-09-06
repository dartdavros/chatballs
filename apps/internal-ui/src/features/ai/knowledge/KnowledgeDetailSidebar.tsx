import type { AgentCard } from "../../agents/model";
import { agentColorOf } from "../../conversations/model";
import { Icon } from "../../../shared/icons";
import { formatDate } from "../../../shared/utils";
import type { KnowledgeItem } from "./types";

export function KnowledgeDetailSidebar({
  agents,
  item,
  openAgent,
}: {
  agents: AgentCard[];
  item: KnowledgeItem;
  openAgent: (agentId: number) => void;
}) {
  const assignedAgents = agents.filter((agent) => agent.knowledge.some((knowledge) => knowledge.id === item.id));

  return (
    <aside className="knowledge-detail-sidebar">
      <section className="knowledge-editor-card knowledge-agents-card">
        <h4>Агенты, использующие знание</h4>
        <p>Выбор знания хранится у агента явно.</p>
        <div className="knowledge-agent-list">
          {assignedAgents.map((agent) => (
            <button type="button" onClick={() => openAgent(agent.id)} key={agent.id}>
              <span style={{ color: agentColorOf(agent.id), background: `color-mix(in srgb, ${agentColorOf(agent.id)} 14%, var(--surface-card))` }}><Icon name="robot" size={16} /></span>
              <div><strong>{agent.name}</strong><small>{agent.groupName ?? "Без группы"}</small></div>
            </button>
          ))}
        </div>
      </section>
      <section className="knowledge-editor-card knowledge-info-card">
        <h4>Сведения</h4>
        <dl>
          <div><dt>ID</dt><dd className="mono">KN-{String(item.id).padStart(5, "0")}</dd></div>
          <div><dt>Фрагментов в индексе</dt><dd>{item.fragmentsCount ?? "—"}</dd></div>
          <div><dt>Создано</dt><dd>{formatDate(item.createdAt)}</dd></div>
          {item.createdBy && <div><dt>Автор</dt><dd>{item.createdBy}</dd></div>}
        </dl>
      </section>
    </aside>
  );
}
