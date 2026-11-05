import { t } from "../../../i18n";
import { FormField } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import { Segmented } from "../../../shared/ui";
import type { ActionMode, AgentAction } from "./model";

export function AgentActionRow({ row, busy, change }: {
  row: AgentAction; busy: boolean; change: (id: string, mode: ActionMode) => void;
}) {
  return <div className="agent-action">
    <div className="agent-action-head"><div><strong>{row.title}</strong><small>{row.available ? row.subtitle : t("agent_actions.unavailable", { name: row.subtitle })}</small></div>
      <Segmented<ActionMode> value={row.mode} setValue={mode => change(row.id, mode)}
        items={(["off", "self", "ask"] as const).map(mode => [mode, t(`agent_actions.${mode}`)])}
        disabledKeys={busy ? ["off", "self", "ask"] : !row.available ? ["self", "ask"] : []} />
    </div>
    {row.mode === "ask" && <div className="agent-action-confirm">
      <FormField label={t("agent_actions.confirmer")} value={t("agent_actions.responsible")} />
      <FormField label={t("agent_actions.deadline")} value={t("agent_actions.thirty_minutes")} />
    </div>}
    {row.mode === "self" && row.writes && <div className="agent-action-warning"><Icon name="warning" size={14} /><span>{t("agent_actions.self_note")}</span></div>}
  </div>;
}
