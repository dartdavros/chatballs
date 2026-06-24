import { Icon } from "../../shared/icons";
import { agentStatus, productAccent, publishedRelease, type AiAgent, type AiRelease } from "./model";

export function AgentsTable({
  agents,
  releases,
  menuId,
  setMenuId,
  toggleActive,
}: {
  agents: AiAgent[];
  releases: AiRelease[];
  menuId: number | null;
  setMenuId: (id: number | null) => void;
  toggleActive: (agent: AiAgent) => void;
}) {
  return (
    <div className="ai-agents-card">
      <div className="ai-agents-scroll">
        <table className="ai-agents-table">
          <thead>
            <tr>
              <th>АГЕНТ</th>
              <th>ПРОДУКТ</th>
              <th>МОДЕЛЬ</th>
              <th>АКТИВНЫЙ RELEASE</th>
              <th>СТАТУС</th>
              <th className="num">ДИАЛОГИ СЕЙЧАС</th>
              <th className="num">КОНВЕРСИЯ</th>
              <th className="actions-col" />
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => {
              const accent = productAccent(agent.product.code);
              const status = agentStatus(agent);
              const release = publishedRelease(releases, agent.product.code);
              return (
                <tr key={agent.id}>
                  <td>
                    <div className="ai-agent-name-cell">
                      <span className="ai-agent-icon"><Icon name="robot" size={20} /></span>
                      <div>
                        <strong>{agent.name}</strong>
                        <span className="ai-agent-code">{agent.product.code}</span>
                      </div>
                    </div>
                  </td>
                  <td><span className="ai-product-tag" style={{ background: accent.bg, color: accent.color }}>{agent.product.name}</span></td>
                  <td className="mono">{agent.model}</td>
                  <td>
                    {release ? (
                      <span className="ai-release-cell"><span className="mono">v{release.version}</span><span className="ai-badge-published">Published</span></span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td><span className="ai-status" style={{ color: status.color }}><span style={{ background: status.dot }} />{status.label}</span></td>
                  <td className="num muted">—</td>
                  <td className="num muted">—</td>
                  <td className="actions-col">
                    <div className="ai-row-actions">
                      <button
                        type="button"
                        className="ai-row-menu-button"
                        onClick={() => setMenuId(menuId === agent.id ? null : agent.id)}
                        aria-label="Действия"
                      >
                        <Icon name="more" size={16} />
                      </button>
                      {menuId === agent.id && (
                        <div className="ai-row-menu">
                          <button type="button" onClick={() => toggleActive(agent)}>
                            {agent.isActive ? "Остановить агента" : "Запустить агента"}
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="ai-agents-footer">
        <span>{agents.length} агента</span>
        <span className="muted">В первой итерации — один sales-agent на продукт</span>
      </div>
    </div>
  );
}
