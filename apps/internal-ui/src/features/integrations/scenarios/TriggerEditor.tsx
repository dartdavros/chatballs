import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { AccessFields, ToggleField } from "./AccessFields";
import { ScheduleFields } from "./ScheduleFields";
import type { Access, EditorCatalog, Trigger } from "./types";

export function TriggerEditor({ trigger, access, catalog, change, onAccess }: {
  trigger: Trigger; access: Access; catalog: EditorCatalog; change: (patch: Partial<Trigger>) => void; onAccess: (next: Access) => void;
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
    {trigger.kind === "ai" && <div className="scenario-form">{catalog.agents.map(agent => <ToggleField key={agent.id} label={agent.name}
      checked={trigger.agents?.includes(agent.id) ?? false} onChange={checked => change({ agents: checked ? [...(trigger.agents ?? []), agent.id] : (trigger.agents ?? []).filter(id => id !== agent.id) })} />)}</div>}
    <AccessFields value={access} catalog={catalog} onChange={onAccess} />
  </div>;
}
