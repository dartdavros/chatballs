import { t } from "../../../i18n";
import { FormField } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import { LoadingState, Segmented } from "../../../shared/ui";
import type { ActionMode } from "./model";
import type { useAgentActions } from "./useAgentActions";
import "./actions.css";

export function AgentActionsCard({ state }: { state: ReturnType<typeof useAgentActions> }) {
  return <section className="agent-card is-side agent-actions-card">
    <h3>{t("agent_actions.title")}</h3><p>{t("agent_actions.description")}</p>
    <div className="agent-actions-body">
      {state.error && <div className="run-notice is-error" role="alert">{state.error}<button type="button" className="link" onClick={() => void state.reload()}>{t("runs.retry")}</button></div>}
      {!state.rows && !state.error && <LoadingState />}
      {state.rows?.length === 0 && <p className="agent-actions-empty">{t("agent_actions.empty")}</p>}
      {state.rows?.map(row => <div className="agent-action" key={row.id}>
        <div className="agent-action-head"><div><strong>{row.title}</strong><small>{row.available ? row.subtitle : t("agent_actions.unavailable", { name: row.subtitle })}</small></div>
          <Segmented<ActionMode> value={row.mode} setValue={mode => state.change(row.id, mode)}
            items={(["off", "self", "ask"] as const).map(mode => [mode, t(`agent_actions.${mode}`)])}
            disabledKeys={state.busy ? ["off", "self", "ask"] : !row.available ? ["self", "ask"] : []} />
        </div>
        {row.mode === "ask" && <div className="agent-action-confirm">
          <FormField label={t("agent_actions.confirmer")} value={t("agent_actions.responsible")} />
          <FormField label={t("agent_actions.deadline")} value={t("agent_actions.thirty_minutes")} />
        </div>}
        {row.mode === "self" && row.writes && <div className="agent-action-warning"><Icon name="warning" size={14} /><span>{t("agent_actions.self_note")}</span></div>}
      </div>)}
      {state.rows && <p className="agent-actions-foot">{t("agent_actions.applies")}</p>}
    </div>
  </section>;
}
