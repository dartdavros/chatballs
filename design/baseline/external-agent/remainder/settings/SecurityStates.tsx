import { DecisionDialog } from '../../../../../apps/internal-ui/src/shared/DecisionDialog';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { tx, type CopyKey } from './copy';
import { KeyCopyButton } from './KeyCopyButton';

export function NewlyCreatedKey() {
  return <section className="administration-card" data-new-key-once>
    <div className="settings-card-head"><div><strong>{tx('newKey')}</strong><small>{tx('newKeyLead')}</small></div></div>
    <div className="employee-password-field"><span>{tx('incoming')}</span>
      <span className="employee-password-value"><code data-one-time-example>{tx('keyExample')}</code>
        <KeyCopyButton />
      </span>
    </div>
    <div className="administration-actions"><Button variant="primary" onClick={() => {}}>{tx('keyDone')}</Button></div>
  </section>;
}

const dialogCopy: Record<string, [CopyKey, CopyKey, CopyKey, CopyKey]> = {
  S25: ['rotateTitle', 'rotateLead', 'rotateRisk', 'rotateAction'],
  S26: ['revokeTitle', 'revokeLead', 'revokeRisk', 'revokeAction'],
  S37: ['disableTitle', 'disableLead', 'disableRisk', 'disableAction'],
};
export function SettingsConfirmation({ variant }: { variant: string }) {
  const keys = dialogCopy[variant];
  if (!keys) return null;
  return <DecisionDialog open onClose={() => {}} tone={variant === 'S26' ? 'danger' : 'warning'}
    icon={variant === 'S26' ? 'errorCircle' : 'alert'} title={tx(keys[0])} description={tx(keys[1])}
    actions={<><Button variant="secondary" onClick={() => {}}>{tx('cancel')}</Button>
      <Button variant={variant === 'S26' ? 'danger-outline' : 'primary'} onClick={() => {}}>{tx(keys[3])}</Button></>}>
    <div className="settings-risk-note"><p>{tx(keys[2])}</p></div>
  </DecisionDialog>;
}
