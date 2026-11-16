import { FormField, SelectField } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { bindingTx } from './binding-copy';
import { tx } from './copy';
import type { AgentBinding, BindingPatch } from './BindingModel';
export type { AgentBinding } from './BindingModel';

export function BindingRow({ binding, index, agents, disabled, onChange, onDelete }: {
  binding: AgentBinding; index: number; agents: [string, string][]; disabled: boolean;
  onChange: (patch: BindingPatch) => void; onDelete: () => void;
}) {
  const agentName = agents.find(([id]) => id === binding.agentId)?.[1] ?? bindingTx('unselected');
  return <div className="service-connect-stack" role="group" aria-label={`${bindingTx('row')} ${index + 1}`}
    data-binding-row={binding.id} data-binding-empty={!binding.agentId && !binding.externalId}>
    <div data-binding-agent><SelectField label={tx('agent')} value={binding.agentId}
      options={agents} disabled={disabled} onChange={agentId => onChange({ agentId })} /></div>
    <div data-binding-external-id><FormField label={tx('externalId')} value={binding.externalId}
      mono disabled={disabled} onChange={externalId => onChange({ externalId })} /></div>
    <div className="settings-card-actions"><Button variant="danger-outline" icon="trash" disabled={disabled}
      aria-label={`${bindingTx('remove')}: ${agentName}`} onClick={onDelete} data-binding-delete>{bindingTx('remove')}</Button></div>
  </div>;
}
