import { useRef, useState } from "react";
import { Button } from "../../../shared/ui-controls";
import { ExternalAgentConnectionFields } from "./ExternalAgentConnectionFields";
import { BindingCard } from "./BindingCard";
import { DataPolicyCard, sameField } from "./DataPolicyCard";
import { ProcessingCard } from "./ProcessingCard";
import { TemplatePolicyCard } from "./TemplatePolicyCard";
import { SettingsSaveFooter } from "./SettingsSaveFooter";
import { SettingsConfirmation, type Confirmation } from "./SettingsConfirmation";
import { useConnectionDraft } from "./useConnectionDraft";
import type { useExternalAgentSettings } from "./useExternalAgentSettings";
import type { ExternalConnection, SettingsCatalog, ExternalBinding } from "./model";
import { et } from "./copy";

export function ConnectionSettings({ organization, connection, catalog, enabled, state }: {
  organization: string; connection: ExternalConnection; catalog: SettingsCatalog; enabled: boolean;
  state: ReturnType<typeof useExternalAgentSettings>;
}) {
  const { previous, draft, edited, setDraft, adoptNext, acceptCheck } = useConnectionDraft(connection);
  const [selectedId, setSelectedId] = useState(connection.bindings[0]?.agentId);
  const [confirmation, setConfirmation] = useState<Confirmation>();
  const connectionSection = useRef<HTMLElement>(null);
  const binding = draft.bindings.find(item => item.agentId === selectedId) ?? draft.bindings[0];
  const targeted = state.activeConnectionId === connection.id;
  const checking = state.busy && targeted && state.operationKind === "check";
  const saving = state.busy && targeted && state.operationKind === "save";
  const disabled = !enabled || state.busy && state.operationKind !== "check";
  const bindingDisabled = disabled || !connection.compatible && !connection.bindings.length;
  const review = enabled && connection.bindings.some(item => !item.policyAccepted);
  const dirty = edited || review;
  const accessDirty = draft.baseUrl !== previous.baseUrl || !!draft.outboundKey || draft.enabled !== previous.enabled;
  function updateBinding(patch: Partial<ExternalBinding>) {
    if (binding) setDraft(current => ({ ...current, bindings: current.bindings.map(item => item.agentId === binding.agentId ? { ...item, ...patch } : item) }));
  }
  async function save() {
    const clean = { ...draft, bindings: draft.bindings.map(item => ({ ...item, policyAccepted: true,
      customFields: item.customFields.filter(ref => catalog.customFields.some(field => sameField(ref, field))),
      templateIds: item.templateIds.filter(id => catalog.templates.some(template => template.id === id)),
    })) };
    adoptNext.current = true;
    if (!await state.save(previous, clean)) adoptNext.current = false;
  }
  const policy = binding ? { name: draft.name, bindings: draft.bindings, binding, catalog, disabled: bindingDisabled,
    select: setSelectedId, change: updateBinding } : null;
  return <>
    <ExternalAgentConnectionFields sectionRef={connectionSection} connection={draft} disabled={disabled} retained={!enabled} review={review} checking={checking}
      failed={targeted && state.error === "check" || !!connection.checkFailure} failure={connection.checkFailure ?? state.checkFailure} dirty={edited} accessDirty={accessDirty}
      change={patch => setDraft(current => ({ ...current, ...patch }))}
      check={() => void state.action(connection.id, "check", "POST", acceptCheck)}
      keyAction={action => { if (action === "create") void state.action(connection.id, "key"); else setConfirmation(action); }} />
    <BindingCard bindings={draft.bindings} agents={catalog.agents} disabled={bindingDisabled} review={review}
      change={bindings => setDraft(current => ({ ...current, bindings }))} />
    {binding && <ProcessingCard binding={binding} connection={draft.name} disabled={bindingDisabled} change={updateBinding} />}
    {policy && <><DataPolicyCard {...policy} /><TemplatePolicyCard {...policy} organization={organization} /></>}
    <SettingsSaveFooter busy={saving} failed={targeted && state.error === "save"} dirty={dirty} disabled={disabled || state.busy}
      save={() => void save()} enableFailed={!enabled && state.featureFailure === "enable"} retryEnable={() => void state.feature(true)} />
    {review && <div className="administration-actions"><Button variant="primary" disabled={disabled}
      onClick={() => connectionSection.current?.scrollIntoView({ block: "start" })}>{et("settings.configure")}</Button></div>}
    {confirmation && <SettingsConfirmation action={confirmation} busy={state.busy} cancel={() => { if (!state.busy) setConfirmation(undefined); }}
      confirm={() => void state.action(connection.id, "key", confirmation === "revoke" ? "DELETE" : "POST").then(ok => { if (ok) setConfirmation(undefined); })} />}
  </>;
}
