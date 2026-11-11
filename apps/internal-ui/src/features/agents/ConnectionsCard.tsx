import { t } from "../../i18n";
import { ChannelNavigationMenu, type ChannelRoute } from "../../shared/ChannelNavigationMenu";
import { ChannelGlyph } from "../../shared/badges";
import { CopyButton } from "../../shared/ui-controls";
import { webWidgetSnippet, type Integration } from "../integrations/model";
import { agentTint, connectionStatusMeta, connectionSubtitle, type AgentCard, type AgentConnection } from "./model";

// --- Подключения (кадры G3/G4) ---

export function ConnectionsCard({ card, canManage, busy, available, openChannels, bind, unbind }: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  available: Integration[];
  openChannels: (route: ChannelRoute) => void;
  bind: (integrationId: number) => void;
  unbind: (integrationId: number) => void;
}) {
  const widget = card.connections.find((connection) => connection.provider === "WEB" && connection.widgetPublicKey);
  return (
    <section className="agent-card is-side">
      <div className="agent-card-head is-tight">
        <h3>{t("common.connections")}</h3>
        {canManage && (
          <ChannelNavigationMenu onNavigate={openChannels} />
        )}
      </div>
      <p>{t("ai.customers_reach_agent_through_these")}</p>
      {card.connections.map((connection) => (
        <ConnectionRow
          connection={connection}
          status={connectionStatusMeta(connection.status)}
          action={canManage ? { label: t("ai.unbind"), run: () => unbind(connection.id) } : null}
          busy={busy}
          key={connection.id}
        />
      ))}
      {canManage && available.map((integration) => (
        <ConnectionRow
          connection={{ id: integration.id, provider: integration.provider, name: integration.name, status: integration.status, botUsername: "", email: "", allowedOrigins: [], widgetPublicKey: "" }}
          subtitle={t("ai.free_connection")}
          status={{ text: t("ai.free"), bg: "var(--n-9)", color: "var(--n-4)" }}
          action={{ label: t("ai.bind"), run: () => bind(integration.id) }}
          busy={busy}
          key={`free-${integration.id}`}
        />
      ))}
      {widget && (
        <div className="agent-widget">
          <div>
            <small>{t("ai.widget_embed_snippet")}</small>
            <CopyButton className="agent-widget-copy" label={t("common.copy")} value={webWidgetSnippet(widget.widgetPublicKey)} />
          </div>
          <code>{webWidgetSnippet(widget.widgetPublicKey)}</code>
          <small>{t("ai.paste_before_lt_body_gt")}</small>
        </div>
      )}
    </section>
  );
}

function ConnectionRow({ connection, subtitle, status, action, busy }: {
  connection: AgentConnection;
  subtitle?: string;
  status: { text: string; bg: string; color: string };
  action: { label: string; run: () => void } | null;
  busy: boolean;
}) {
  const tint = agentTint(connection.provider);
  return (
    <div className="agent-connection">
      <span className="agent-connection-tile" style={{ background: tint.bg, color: tint.color }}>
        <ChannelGlyph provider={connection.provider} size={16} />
      </span>
      <div>
        <strong>{connection.name}</strong>
        <small>{subtitle ?? connectionSubtitle(connection)}</small>
      </div>
      <b className="agent-chip" style={{ background: status.bg, color: status.color }}>{status.text}</b>
      {action && <button className="agent-connection-action" type="button" disabled={busy} onClick={action.run}>{action.label}</button>}
    </div>
  );
}
