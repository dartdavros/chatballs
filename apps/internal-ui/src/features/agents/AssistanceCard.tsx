import { t } from "../../i18n";
import { SwitchButton } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import type { AgentCard } from "./model";
import { useAgentAssistance } from "./useAgentAssistance";
import "./assistance.css";
import { et } from "../settings/external-agent/copy";

/** platform-expansion/Сотрудники и агенты.dc.html, G1–G3. */
export function AssistanceCard({ card, canManage, busy, save }: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  save: (enabled: boolean) => Promise<boolean>;
}) {
  const state = useAgentAssistance(card.assistanceEnabled, busy, save);
  const aiActive = card.aiStatus === "ACTIVE";
  const disabled = !canManage || busy || state.saving;

  return (
    <section className={`agent-card is-side agent-assistance${state.saving ? " is-saving" : ""}${state.failed ? " is-error" : ""}`} aria-busy={state.saving}>
      <h3>{t("agent_assistance.title")}<i title={t("agent_assistance.new_block")} /></h3>
      <p>{t("agent_assistance.description")}</p>
      <div className="agent-assistance-toggle">
        <div>
          <strong>{t("agent_assistance.drafts")}</strong>
          <small>{t(aiActive ? "agent_assistance.independent" : "agent_assistance.ai_stopped")}</small>
        </div>
        <SwitchButton className="ui-switch is-compact" label={t("agent_assistance.drafts")} checked={state.checked} disabled={disabled} onClick={() => void state.toggle()} />
      </div>
      <div className="agent-assistance-toggle">
        <div>
          <strong>{t("agent_assistance.autonomous")}</strong>
          <small>{card.executionMode === "external" ? et("agent.assistanceHelp") : t("agent_assistance.autonomous_description")}</small>
        </div>
        <SwitchButton className="ui-switch is-compact is-comparison" label={t("agent_assistance.autonomous")} checked={aiActive} disabled onClick={() => {}} />
      </div>
      {state.failed ? (
        <>
          <div className="agent-assistance-note is-error" role="alert">
            <Icon name="errorCircle" size={14} strokeWidth={2} />
            <span>{t("agent_assistance.save_error", { state: t(card.assistanceEnabled ? "agent_assistance.remained_enabled" : "agent_assistance.remained_disabled") })}</span>
          </div>
          <div className="agent-assistance-footer">
            <button type="button" disabled={disabled} onClick={() => void state.retry()}>{t("agent_assistance.retry")}</button>
          </div>
        </>
      ) : (
        <div className="agent-assistance-footer" role="status">
          <small>{t(state.saving ? "agent_assistance.saving" : card.assistanceEnabled ? "agent_assistance.enabled" : "agent_assistance.disabled")}</small>
        </div>
      )}
      {card.providerIntegrationId === null && (
        <div className="agent-assistance-note is-warning">
          <Icon name="warning" size={14} strokeWidth={2} />
          <span>{card.executionMode === "external" ? et("agent.assistanceMissing") : t("agent_assistance.no_provider")}</span>
        </div>
      )}
    </section>
  );
}
