import { agentColorOf } from "../conversations/model";
import { Icon } from "../../shared/icons";
import { PROVIDERS, type Integration } from "./model";
import { ConnectionIcon, RowActions, StatusCell } from "./rows";

// Подстрока подключения (SPEC-CHATBALLS-0025 §2.4): провайдер + идентификатор.
function subtitle(integration: Integration): string {
  const label = PROVIDERS[integration.provider].label;
  const { config } = integration;
  if (integration.provider === "EMAIL") return config.email ? `${label} · ${config.email}` : label;
  if (config.purpose === "notifications") return `${label} · сервисный бот уведомлений`;
  if (config.botUsername) return `${label} · @${config.botUsername}`;
  if (config.botName) return `${label} · ${config.botName}`;
  return label;
}

type ConnectionsTableProps = {
  items: Integration[];
  testingId: number | null;
  onTest: (integration: Integration) => void;
  onEdit: (integration: Integration) => void;
  onToggleActive: (integration: Integration) => void;
  onDelete: (integration: Integration) => void;
};

export function ConnectionsTable({ items, testingId, onTest, onEdit, onToggleActive, onDelete }: ConnectionsTableProps) {
  return (
    <div className="table-card">
      <table className="baseline-table">
        <thead>
          <tr>
            <th>НАЗВАНИЕ</th>
            <th>АГЕНТ</th>
            <th>СТАТУС</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="product-cell">
                  <ConnectionIcon provider={item.provider} />
                  <span><strong>{item.name}</strong><small>{subtitle(item)}</small></span>
                </div>
              </td>
              <td>
                {item.channel
                  ? (
                    <span className="integration-agent" style={{ color: agentColorOf(item.channel.id) }}>
                      <Icon name="robot" size={14} />{item.channel.name}
                    </span>
                  )
                  : <span className="product-empty-value">—</span>}
              </td>
              <td><StatusCell integration={item} /></td>
              <td className="row-actions">
                <RowActions integration={item} testing={testingId === item.id} onTest={onTest} onEdit={onEdit} onToggleActive={onToggleActive} onDelete={onDelete} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
