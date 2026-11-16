import { useState } from "react";
import { SelectField } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import { HelpTrigger } from "../../settings/external-agent/HelpTrigger";
import { et } from "../../settings/external-agent/copy";
import type { AgentCard, AgentPatch } from "../model";

export function AgentExecutionCard({ card, canManage, busy, apply, openSettings }: {
  card: AgentCard; canManage: boolean; busy: boolean; apply: (patch: AgentPatch) => Promise<boolean>; openSettings: () => void;
}) {
  const [attempted, setAttempted] = useState(false);
  const [returned, setReturned] = useState(false);
  if (!card.externalExecutionEnabled && card.executionMode !== "external") return null;
  const external = card.executionMode === "external";
  const execution = card.externalExecution;
  const reason = !card.externalExecutionEnabled ? "disabled" : execution?.reason ?? "notReady";
  const blocked = external && !execution?.available;
  return <section className="agent-card" data-execution-mode={external ? "external" : "builtin"}>
    <div className="agent-card-head"><span className="external-help-title"><h3>{et("agent.executionTitle")}</h3><HelpTrigger topic="external" /></span></div>
    {!blocked && card.aiStatus !== "ACTIVE" && (external || returned) && <p className="settings-section-note">{et(external ? "agent.paused" : "agent.returned")}</p>}
    <div className="agent-side-fields"><SelectField label={et("agent.method")} value={external ? "external" : "builtin"}
      disabled={busy || !card.externalExecutionEnabled} readOnly={!canManage}
      options={[["builtin", et("agent.builtin")], ["external", et("agent.external")]]} onChange={value => {
        if (value === "external" && !execution?.available) { setAttempted(true); return; }
        setAttempted(false); setReturned(false);
        void apply({ executionMode: value as "builtin" | "external" }).then(saved => { if (saved && external && value === "builtin") setReturned(true); });
      }} />
      {external && <SelectField label={et("agent.executor")} value={execution?.connectionId ? String(execution.connectionId) : ""}
        options={execution?.connectionId ? [[String(execution.connectionId), execution.name]] : [["", "—"]]}
        disabled={busy || !card.externalExecutionEnabled} readOnly={!canManage} onChange={() => undefined} />}
      {(blocked || attempted) && <div className="agent-feedback is-warning" role="alert">{et(`agent.${reason}`)}</div>}
      <div className="agent-card-head is-tight"><StatusPill status={blocked ? "disabled" : "healthy"}
        label={et(blocked ? "agent.unavailableLabel" : external ? "agent.ready" : "agent.builtin")} />
        {canManage && <button type="button" className="link has-icon" onClick={openSettings}>{et("agent.settings")}<Icon name="external" size={13} /></button>}</div>
      {external && <small className="settings-section-note">{et(card.providerIntegrationId === null ? "agent.missingLlm" : "agent.preserved")}</small>}
    </div>
  </section>;
}
