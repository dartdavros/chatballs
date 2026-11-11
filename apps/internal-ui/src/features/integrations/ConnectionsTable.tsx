import { agentColorOf } from "../conversations/model";
import { Icon } from "../../shared/icons";
import { PROVIDERS, type Integration } from "./model";
import { ConnectionIcon, RowActions, StatusCell } from "./rows";
import { t, tn } from "../../i18n";
import { serverHost } from "./external/model";
import "./connections-table.css";

// Подстрока подключения (SPEC-CHATBALLS-0025 §2.4): провайдер + идентификатор.
function subtitle(integration: Integration): string {
  const label = PROVIDERS[integration.provider].label;
  if (integration.externalServer) return `${label} · ${serverHost(integration.externalServer.url)}`;
  const { config } = integration;
  if (integration.provider === "EMAIL") return config.email ? `${label} · ${config.email}` : label;
  if (config.purpose === "notifications") return t("settings.service_notification_bot_named", { name: label });
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
  context?: "channels" | "servers";
};

export function ConnectionsTable({ items, testingId, onTest, onEdit, onToggleActive, onDelete, context }: ConnectionsTableProps) {
  return (
    <>
      <div className="table-card">
        <table className="baseline-table integrations-connections-table">
          <thead>
            <tr>
              <th>{t("settings.title")}</th>
              <th>{t(context === "servers" ? "ai.tools" : context === "channels" ? "navigation.routing" : "servers.agent_tools")}</th>
              <th>{t("common.status_2")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  <div className="product-cell">
                    <ConnectionIcon provider={item.provider} />
                    <span>{item.provider === "WEB" || item.kind === "EXTERNAL_SERVER"
                      ? <button className="link is-strong" type="button" onClick={() => onEdit(item)}>{item.name}</button>
                      : <strong>{item.name}</strong>}<small>{subtitle(item)}</small></span>
                  </div>
                </td>
                <td>
                  {item.externalServer ? <span className="integration-tools-count"><Icon name="wrench" size={14} />{tn("servers.count", item.externalServer.type === "http" ? 1 : item.externalServer.tools?.length ?? 0)}</span> : item.channel?.hasAgent
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
      {context !== "channels" && <p className="integrations-list-note">{t("servers.list_note")}</p>}
    </>
  );
}
