import { useRef, useState } from 'react';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { HelpTrigger } from '../shared/HelpTrigger';
import { BindingRow } from './BindingRow';
import { BindingAddDialog } from './BindingAddDialog';
import { BindingRemoveDialog } from './BindingRemoveDialog';
import { availableBindingAgents, normalizedBindingDraft, type AgentBinding, type BindingDraft, type BindingPatch } from './BindingModel';
import { bindingTx } from './binding-copy';
import { tx } from './copy';

export function BindingCard({ disabled = false, review = false, onDirty }: { disabled?: boolean; review?: boolean; onDirty?: () => void }) {
  const agents: [string, string][] = [['support', tx('supportAgent')], ['sales', tx('salesAgent')]];
  const [bindings, setBindings] = useState<AgentBinding[]>(() => [
    { id: 1, agentId: 'support', externalId: tx('supportId') },
    { id: 2, agentId: 'sales', externalId: tx('salesId') },
  ]);
  const nextId = useRef(3);
  const [adding, setAdding] = useState(false), [removingId, setRemovingId] = useState<number | null>(null);
  const unbound = availableBindingAgents(agents, bindings), canAdd = !disabled && unbound.length > 0;
  const removing = bindings.find(binding => binding.id === removingId);
  function change(id: number, patch: BindingPatch) {
    const binding = bindings.find(item => item.id === id);
    if (disabled || !binding || Object.entries(patch).every(([key, value]) => binding[key as keyof BindingDraft] === value)) return;
    if (patch.agentId !== undefined && !availableBindingAgents(agents, bindings, id).some(([agentId]) => agentId === patch.agentId)) return;
    setBindings(current => current.map(item => item.id === id ? { ...item, ...patch } : item)); onDirty?.();
  }
  function add(draft: BindingDraft) {
    const normalized = normalizedBindingDraft(draft, unbound);
    if (!canAdd || !adding || !normalized) return;
    const id = nextId.current++;
    setBindings(current => [...current, { id, ...normalized }]); setAdding(false);
    onDirty?.();
  }
  function remove() {
    if (disabled || !removing) return;
    setBindings(current => current.filter(binding => binding.id !== removing.id)); setRemovingId(null); onDirty?.();
  }
  return <section className="administration-card" data-agent-bindings data-bindings-count={bindings.length}>
    <div className="settings-card-head"><div><span className="external-help-title"><strong>{tx('binding')}</strong><HelpTrigger topic="bindings" /></span><small>{tx('bindingHelp')}</small></div></div>
    {review && <div className="administration-message error" role="alert">{tx('reviewLead')}</div>}
    <div className="administration-fields">
      {bindings.map((binding, index) => <BindingRow key={binding.id} binding={binding} index={index}
        agents={availableBindingAgents(agents, bindings, binding.id)}
        disabled={disabled} onChange={patch => change(binding.id, patch)} onDelete={() => { if (!disabled) setRemovingId(binding.id); }} />)}
    </div>
    {bindings.length === 0 && <p className="settings-section-note" data-binding-empty-state>{bindingTx('empty')}</p>}
    <div className="settings-card-actions"><Button variant="secondary" icon="plus" disabled={!canAdd} onClick={() => setAdding(true)} data-binding-add>{bindingTx('add')}</Button></div>
    {!unbound.length && <p className="settings-section-note" data-binding-add-hint>{bindingTx('allBound')}</p>}
    {adding && <BindingAddDialog agents={unbound} disabled={disabled} onCancel={() => setAdding(false)} onAdd={add} />}
    {removing && <BindingRemoveDialog agentName={agents.find(([id]) => id === removing.agentId)?.[1] ?? bindingTx('unselected')}
      bindingId={removing.id} disabled={disabled} onCancel={() => setRemovingId(null)} onConfirm={remove} />}
  </section>;
}
