import { HelpTitle } from "./HelpTitle";
import { useState } from "react";
import { Modal } from "antd";
import { FormField, SelectField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { DecisionDialog } from "../../../shared/DecisionDialog";
import { emptyBinding } from "./bindings";
import { et } from "./copy";
import type { ExternalBinding, SettingsCatalog } from "./model";

export function BindingCard({ bindings, agents, disabled, review = false, change }: {
  bindings: ExternalBinding[]; agents: SettingsCatalog["agents"]; disabled: boolean;
  review?: boolean;
  change: (bindings: ExternalBinding[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<number>();
  const [agentId, setAgentId] = useState("");
  const [externalId, setExternalId] = useState("");
  const available = agents.filter(agent => !bindings.some(binding => binding.agentId === agent.id));
  const selected = available.find(agent => String(agent.id) === agentId);
  const update = (index: number, patch: Partial<ExternalBinding>) => change(bindings.map((binding, position) => position === index ? { ...binding, ...patch } : binding));
  function add() {
    if (disabled || !selected || !externalId.trim()) return;
    change([...bindings, emptyBinding(selected, externalId)]); setAdding(false); setAgentId(""); setExternalId("");
  }
  return <section className="administration-card" data-agent-bindings>
    <div className="settings-card-head"><div><HelpTitle title={et("settings.binding")} topic="bindings" /><small>{et("settings.bindingHelp")}</small></div></div>
    {review && <div className="administration-message error" role="alert">{et("settings.reviewLead")}</div>}
    <div className="administration-fields">{bindings.map((binding, index) => <div className="service-connect-stack" key={binding.agentId}
      role="group" aria-label={`${et("binding.row")} ${index + 1}`}>
      <div><SelectField label={et("settings.agent")} value={String(binding.agentId)} disabled={disabled}
        options={agents.filter(agent => agent.id === binding.agentId || available.includes(agent)).map(agent => [String(agent.id), agent.name])}
        onChange={value => { const next = agents.find(agent => String(agent.id) === value); if (next) change(bindings.map((item, position) => position === index ? emptyBinding(next, binding.externalAgentId) : item)); }} /></div>
      <div><FormField label={et("settings.externalId")} value={binding.externalAgentId} mono disabled={disabled} onChange={externalAgentId => update(index, {
        externalAgentId, standardFields: [], customFields: [], templateIds: [], proactiveEnabled: false, policyAccepted: false, staleGrants: undefined,
      })} /></div>
      <div className="settings-card-actions"><Button variant="danger-outline" icon="trash" disabled={disabled} onClick={() => setRemoving(binding.agentId)}>{et("binding.remove")}</Button></div>
    </div>)}</div>
    {!bindings.length && <p className="settings-section-note">{et("binding.empty")}</p>}
    <div className="settings-card-actions"><Button variant="secondary" icon="plus" disabled={disabled || !available.length} onClick={() => setAdding(true)}>{et("binding.add")}</Button></div>
    {!available.length && <p className="settings-section-note">{et("binding.allBound")}</p>}
    {adding && <Modal className="agent-create-modal binding-add-modal" open width={440} centered title={et("binding.addTitle")}
      onCancel={() => setAdding(false)} footer={null} destroyOnHidden>
      <form onSubmit={event => { event.preventDefault(); add(); }}><p className="agent-create-lead">{et("binding.addLead")}</p>
        <div className="agent-create-fields"><SelectField label={et("settings.agent")} value={agentId} disabled={disabled}
          options={[["", et("binding.choose")], ...available.map(agent => [String(agent.id), agent.name] as [string, string])]} onChange={setAgentId} />
          <FormField label={et("settings.externalId")} value={externalId} disabled={disabled} mono onChange={setExternalId} /></div>
        <div className="agent-create-actions"><Button variant="secondary" onClick={() => setAdding(false)}>{et("binding.cancel")}</Button>
          <Button variant="primary" type="submit" disabled={disabled || !selected || !externalId.trim()}>{et("binding.addConfirm")}</Button></div>
      </form></Modal>}
    {removing !== undefined && <DecisionDialog className="binding-remove-modal" open width={440} centered onClose={() => setRemoving(undefined)} tone="danger" icon="trash"
      title={et("binding.removeTitle")} description={<strong>{bindings.find(binding => binding.agentId === removing)?.agentName ?? et("binding.unselected")}</strong>}
      actions={<><Button variant="secondary" disabled={disabled} onClick={() => setRemoving(undefined)}>{et("binding.cancel")}</Button>
        <Button variant="danger-outline" disabled={disabled} onClick={() => { change(bindings.filter(binding => binding.agentId !== removing)); setRemoving(undefined); }}>{et("binding.removeConfirm")}</Button></>}>
      <div><p>{et("binding.removeLead")}</p></div></DecisionDialog>}
  </section>;
}
