import { FormField } from '../../../../apps/internal-ui/src/shared/form-controls';
import { Button } from '../../../../apps/internal-ui/src/shared/ui-controls';
import { StatusPill } from '../../../../apps/internal-ui/src/shared/ui';
import { tx } from './copy';

export function ServiceAccess() {
  return <>
    <section className="service-connect-fields" data-access-direction="outgoing">
      <div className="settings-card-head"><div><strong>{tx('outgoingTitle')}</strong><small>{tx('outgoingHelp')}</small></div></div>
      <div className="service-field">
        <FormField label={tx('outgoingKey')} type="password" value="" mono onChange={() => {}} />
        <small>{tx('outgoingKeyHint')}</small>
      </div>
      <p className="service-connect-note">{tx('checkHint')}</p>
      <div className="settings-card-actions"><Button variant="secondary" disabled>{tx('checkConnection')}</Button></div>
    </section>
    <section className="service-connect-fields" data-access-direction="incoming">
      <div className="settings-card-head">
        <div><strong>{tx('incomingTitle')}</strong><small>{tx('incomingHelp')}</small></div>
      </div>
      <span data-incoming-key-state="absent"><StatusPill status="unchecked" label={tx('keyAbsent')} /></span>
      <p className="service-connect-note">{tx('incomingKeyHint')}</p>
      <div className="settings-card-actions" data-create-key><Button variant="secondary" onClick={() => {}}>{tx('createKey')}</Button></div>
    </section>
  </>;
}
