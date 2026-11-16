import { DecisionDialog } from '../../../../../apps/internal-ui/src/shared/DecisionDialog';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { bindingTx } from './binding-copy';

export function BindingRemoveDialog({ agentName, bindingId, disabled, onCancel, onConfirm }: {
  agentName: string; bindingId: number; disabled: boolean; onCancel: () => void; onConfirm: () => void;
}) {
  return <DecisionDialog className="binding-remove-modal" open width={440} centered tone="danger" icon="trash"
    title={bindingTx('removeTitle')} description={<strong>{agentName}</strong>} onClose={onCancel}
    actions={<><Button variant="secondary" onClick={onCancel} data-binding-remove-cancel>{bindingTx('cancel')}</Button>
      <Button variant="danger-outline" disabled={disabled} onClick={onConfirm} data-binding-remove-confirm>{bindingTx('removeConfirm')}</Button></>}>
    <div data-binding-remove-dialog data-binding-remove-id={bindingId}><p>{bindingTx('removeLead')}</p></div>
  </DecisionDialog>;
}
