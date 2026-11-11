import { SwitchButton } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { t } from "../../i18n";
import {
  toggledToolRefs,
  toolServerKind,
  toolServerReason,
  toolServerState,
  toolsLine,
  type AgentTool,
  type AgentToolRef,
  type AgentToolServer,
} from "./agentTools";
import type { AgentToolsState } from "./useAgentTools";

// --- Инструменты (кадры G3–G6, G9) ---

export function AgentToolsCard({ tools, modelWarning, canManage, canOpenServers, busy, save, openIntegrations, openServer }: {
  tools: AgentToolsState;
  /** Инструменты включены, а модель ответов их не вызывает (кадр G6). */
  modelWarning: boolean;
  canManage: boolean;
  canOpenServers: boolean;
  busy: boolean;
  save: (refs: AgentToolRef[]) => void;
  openIntegrations: () => void;
  openServer: (integrationId: number) => void;
}) {
  const { servers, failed, reload } = tools;
  return (
    <section className="agent-card is-side">
      <div className="agent-card-head is-tight">
        <div><h3>{t("ai.tools")}</h3>{servers && <small>{toolsLine(servers)}</small>}</div>
        {canOpenServers && servers && (
          <button className="link has-icon" type="button" onClick={openIntegrations}>{t("navigation.tools")}<Icon name="external" size={13} strokeWidth={2.2} /></button>
        )}
      </div>
      <p>{t("ai.tools_about")}</p>
      {modelWarning && (
        <div className="agent-tools-warning">
          <Icon name="warning" size={15} strokeWidth={2} />
          <small>{t("ai.tools_model_unsupported")}</small>
        </div>
      )}
      {failed && (
        <div className="agent-tools-failed">
          <strong>{t("ai.tools_load_failed")}</strong>
          <small>{t("ai.tools_load_failed_hint")}</small>
          <button className="agent-inline-button" type="button" onClick={reload}>{t("common.try_again")}</button>
        </div>
      )}
      {!failed && !servers && <div className="agent-tools-loading" aria-busy="true"><i /><i /><i /></div>}
      {servers && servers.length === 0 && (
        <div className="agent-tools-empty">
          <p>{t("ai.tools_empty")}</p>
          {canOpenServers && (
            <button className="link has-icon" type="button" onClick={openIntegrations}>{t("ai.tools_connect_server")}<Icon name="external" size={13} strokeWidth={2.2} /></button>
          )}
        </div>
      )}
      {servers?.map((server) => (
        <ToolServerGroup
          server={server}
          canManage={canManage}
          canOpenServers={canOpenServers}
          busy={busy}
          toggle={(tool) => save(toggledToolRefs(servers, server.integrationId, tool.name))}
          openServer={() => openServer(server.integrationId)}
          key={server.integrationId}
        />
      ))}
    </section>
  );
}

function ToolServerGroup({ server, canManage, canOpenServers, busy, toggle, openServer }: {
  server: AgentToolServer;
  canManage: boolean;
  canOpenServers: boolean;
  busy: boolean;
  toggle: (tool: AgentTool) => void;
  openServer: () => void;
}) {
  const state = toolServerState(server);
  const reason = toolServerReason(server);
  return (
    <div className="agent-tools-group">
      <div className="agent-tools-server">
        <span><Icon name={server.type === "http" ? "swap" : "server"} size={13} strokeWidth={2} /></span>
        <strong>{server.name}</strong>
        <small>{toolServerKind(server)}</small>
        {state === "disabled" && <b className="agent-chip is-muted">{t("ai.off")}</b>}
        {state === "error" && <b className="agent-chip is-error">{t("common.error")}</b>}
      </div>
      {state !== "ok" && (
        <small className="agent-tools-reason">
          {reason}{" "}
          {canOpenServers && <button className="link" type="button" onClick={openServer}>{t("ai.tools_open_server")}</button>}
        </small>
      )}
      <div className={state === "ok" ? undefined : "agent-tools-muted"}>
        {server.tools.map((tool) => {
          const locked = state === "ok" && !tool.readOnly;
          return (
            <div className="agent-tool" key={tool.name}>
              <div>
                <span><strong>{tool.title}</strong><small>{tool.description}</small></span>
                <SwitchButton
                  className="ui-switch is-compact"
                  label={t("ai.tool_enabled_label", { tool: tool.title })}
                  checked={tool.enabled}
                  disabled={!canManage || busy || state !== "ok" || locked}
                  onClick={() => toggle(tool)}
                />
              </div>
              {locked && (
                <small className="agent-tool-locked">
                  <Icon name="warning" size={12} strokeWidth={2.2} />
                  <span>
                    {t("ai.tool_may_change_data")}{" "}
                    {canOpenServers
                      ? <button className="link" type="button" onClick={openServer}>{t("ai.tool_confirm_in_server")}</button>
                      : t("ai.tool_confirm_in_server")}
                    {t("ai.tool_if_only_reads")}
                  </span>
                </small>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
