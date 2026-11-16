import { useState } from 'react';
import { Modal } from 'antd';
import { FormField, SelectField } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import '../../../../../apps/internal-ui/src/features/agents/styles.css';
import { normalizedBindingDraft, type BindingAgent, type BindingDraft } from './BindingModel';
import { bindingTx } from './binding-copy';
import { tx } from './copy';

export function BindingAddDialog({ agents, disabled, onCancel, onAdd }: {
  agents: BindingAgent[]; disabled: boolean; onCancel: () => void; onAdd: (draft: BindingDraft) => void;
}) {
  const [draft, setDraft] = useState<BindingDraft>({ agentId: '', externalId: '' });
  const valid = !disabled && normalizedBindingDraft(draft, agents);
  return <Modal className="agent-create-modal binding-add-modal" open width={440} centered title={bindingTx('addTitle')}
    onCancel={onCancel} footer={null} destroyOnHidden>
    <form data-binding-add-dialog onSubmit={event => { event.preventDefault(); if (valid) onAdd(valid); }}>
      <p className="agent-create-lead">{bindingTx('addLead')}</p>
      <div className="agent-create-fields">
        <div data-binding-draft-agent><SelectField label={tx('agent')} value={draft.agentId} disabled={disabled}
          options={[[ '', bindingTx('choose') ], ...agents]} onChange={agentId => setDraft(current => ({ ...current, agentId }))} /></div>
        <div data-binding-draft-external-id><FormField label={tx('externalId')} value={draft.externalId} disabled={disabled}
          mono onChange={externalId => setDraft(current => ({ ...current, externalId }))} /></div>
      </div>
      <div className="agent-create-actions"><Button variant="secondary" onClick={onCancel} data-binding-add-cancel>{bindingTx('cancel')}</Button>
        <Button variant="primary" type="submit" disabled={!valid} data-binding-add-confirm>{bindingTx('addConfirm')}</Button></div>
    </form>
  </Modal>;
}
