import { Dropdown } from "antd";

import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { ToneBadge } from "../../shared/ui-controls";
import { productAccent } from "../../shared/utils";
import type { AiAgent } from "./model";

export function AgentsTable({
  agents,
  menuId,
  setMenuId,
  toggleActive,
  openAgent,
}: {
  agents: AiAgent[];
  menuId: number | null;
  setMenuId: (id: number | null) => void;
  toggleActive: (agent: AiAgent) => void;
  openAgent: (agentId: number) => void;
}) {
  return (
    <div className="table-card">
      <div className="ai-agents-scroll">
        <table className="baseline-table">
          <thead>
            <tr>
              <th>АГЕНТ</th>
              <th>КАНАЛ</th>
              <th>МОДЕЛЬ</th>
              <th className="numeric">ЗНАНИЯ</th>
              <th>СТАТУС</th>
              <th className="numeric">ДИАЛОГИ СЕЙЧАС</th>
              <th className="numeric">КОНВЕРСИЯ</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => {
              const accent = productAccent(agent.channel.code);
              const menuItems = [
                { key: "open", label: <button type="button" onClick={() => { setMenuId(null); openAgent(agent.id); }}><Icon name="external" size={15} />Открыть агента</button> },
                { type: "divider" as const },
                {
                  key: "toggle",
                  label: (
                    <button type="button" className={agent.isActive ? "warning" : ""} onClick={() => toggleActive(agent)}>
                      <Icon name={agent.isActive ? "pause" : "bolt"} size={15} />
                      {agent.isActive ? "Остановить агента" : "Запустить агента"}
                    </button>
                  ),
                },
              ];
              return (
                <tr key={agent.id}>
                  <td>
                    <div className="product-cell">
                      <span className="product-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="robot" size={21} /></span>
                      <span>
                        <button className="ai-agent-name-link" type="button" onClick={() => openAgent(agent.id)}>{agent.name}</button>
                        <small>{agent.channel.code}</small>
                      </span>
                    </div>
                  </td>
                  <td><ToneBadge bg={accent.bg} color={accent.color}>{agent.channel.name}</ToneBadge></td>
                  <td><code className="ai-mono">{agent.model}</code></td>
                  <td className="numeric">{agent.knowledge.length > 0 ? agent.knowledge.length : <span className="product-empty-value">—</span>}</td>
                  <td><StatusPill status={agent.isActive ? "active" : "disabled"} /></td>
                  <td className="numeric"><span className="product-empty-value">—</span></td>
                  <td className="numeric"><span className="product-empty-value">—</span></td>
                  <td className="row-actions">
                    <div className="ai-row-actions">
                      <Dropdown
                        menu={{ items: menuItems }}
                        open={menuId === agent.id}
                        onOpenChange={(open) => setMenuId(open ? agent.id : null)}
                        trigger={["click"]}
                        overlayClassName="product-actions-dropdown"
                      >
                        <button className="row-menu-button" aria-label="Действия агента"><Icon name="more" /></button>
                      </Dropdown>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="ai-table-footer">
        <span>{agents.length} агента</span>
        <span>Один агент на канал обработки</span>
      </div>
    </div>
  );
}
