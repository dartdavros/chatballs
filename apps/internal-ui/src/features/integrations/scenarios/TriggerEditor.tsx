import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { AccessFields } from "./AccessFields";
import { ScheduleFields } from "./ScheduleFields";
import type { Access, EditorCatalog, Trigger, Scenario } from "./types";

export function TriggerEditor({ trigger, access, catalog, change, onAccess, policies, onPolicy }: {
  trigger: Trigger; access: Access; catalog: EditorCatalog; change: (patch: Partial<Trigger>) => void; onAccess: (next: Access) => void;
  policies?: Scenario["agentPolicies"]; onPolicy: (agent: number, mode: "off" | "self" | "ask") => void;
}) {
  const adapter = catalog.adapters.find(a => a.key === catalog.connections.find(c => String(c.id) === trigger.connection)?.adapter);
  return <div className="scenario-form">
    {trigger.kind === "service" && <SelectField label={t("scenarios.connection")} value={trigger.connection ?? ""}
      options={[["", t("scenarios.select")], ...catalog.connections.map(c => [String(c.id), c.name] as [string, string])]}
      onChange={connection => change({ connection, event: "" })} wide />}
    {(trigger.kind === "chatballs" || trigger.kind === "service") && <SelectField label={t("scenarios.event")} value={trigger.event ?? ""}
      options={[["", t("scenarios.select")], ...(trigger.kind === "chatballs" ? catalog.events : adapter?.events ?? []).map(event => [event.key, event.title] as [string, string])]}
      onChange={event => change({ event })} wide />}
    {trigger.kind === "schedule" && <ScheduleFields trigger={trigger} timezone={catalog.timezone} change={change} />}
    {trigger.kind === "ai" && (trigger.agents?.length ? trigger.agents : [0]).map((agent, index) => <div className="scenario-form" key={index}>
      <SelectField label={t("common.agent")} value={String(agent || "")} options={[["", t("scenarios.select")], ...catalog.agents.map(row => [String(row.id), row.name] as [string, string])]}
        onChange={value => { const next = Number(value); const agents = [...(trigger.agents ?? [])]; agents[index] = next; change({ agents: agents.filter(Boolean) }); if (next) onPolicy(next, policies?.find(row => row.agent === next)?.mode ?? "off"); }} wide />
      {!!agent && <SelectField label={t("scenarios.ai_mode")} value={policies?.find(row => row.agent === agent)?.mode ?? "off"}
        options={(["off", "ask", "self"] as const).map(mode => [mode, t(`agent_actions.${mode}`)])}
        onChange={mode => onPolicy(agent, mode as "off" | "self" | "ask")} wide />}
    </div>)}
    <AccessFields value={access} catalog={catalog} onChange={onAccess} />
  </div>;
}
