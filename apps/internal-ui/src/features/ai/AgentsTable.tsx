import { Dropdown } from "antd";

import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { MonoLink, ToneBadge } from "../../shared/ui-controls";
import { productAccent } from "../../shared/utils";
import { publishedRelease, type AiAgent, type AiRelease } from "./model";

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
    <div className="table-card">
      <div className="ai-agents-scroll">
        <table className="baseline-table">
          <thead>
            <tr>
              <th>АГЕНТ</th>
              <th>ПРОДУКТ</th>
              <th>МОДЕЛЬ</th>
              <th>АКТИВНЫЙ RELEASE</th>
              <th>СТАТУС</th>
              <th className="numeric">ДИАЛОГИ СЕЙЧАС</th>
              <th className="numeric">КОНВЕРСИЯ</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => {
              const accent = productAccent(agent.product.code);
              const release = publishedRelease(releases, agent.product.code);
              const menuItems = [
                { key: "open", disabled: true, label: <button type="button"><Icon name="external" size={15} />Открыть агента</button> },
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
                      <span><strong>{agent.name}</strong><small>{agent.product.code}</small></span>
                    </div>
                  </td>
                  <td><ToneBadge bg={accent.bg} color={accent.color}>{agent.product.name}</ToneBadge></td>
                  <td><code className="ai-mono">{agent.model}</code></td>
                  <td>
                    {release ? (
                      <span className="ai-release-cell"><MonoLink>{`v${release.version}`}</MonoLink><ToneBadge bg="#f6ffed" color="#389e0d">Published</ToneBadge></span>
                    ) : (
                      <span className="product-empty-value">—</span>
                    )}
                  </td>
                  <td><StatusPill status={agent.isActive ? "active" : "disabled"} /></td>
                  <td className="numeric"><span className="product-empty-value">—</span></td>
                  <td className="numeric"><span className="product-empty-value">—</span></td>
                  <td className="row-actions">
                    <Dropdown
                      menu={{ items: menuItems }}
                      open={menuId === agent.id}
                      onOpenChange={(open) => setMenuId(open ? agent.id : null)}
                      trigger={["click"]}
                      overlayClassName="product-actions-dropdown"
                    >
                      <button className="row-menu-button" aria-label="Действия агента"><Icon name="more" /></button>
                    </Dropdown>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="ai-table-footer">
        <span>{agents.length} агента</span>
        <span className="product-empty-value">В первой итерации — один sales-agent на продукт</span>
      </div>
    </div>
  );
}
