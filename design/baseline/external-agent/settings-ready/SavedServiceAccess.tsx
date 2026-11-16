import { Button } from '../../../../apps/internal-ui/src/shared/ui-controls';
import { MaskedKeyField } from './MaskedKeyField';
import { CapabilitiesResult } from './CapabilitiesResult';
import { tx } from './copy';

export function SavedServiceAccess() {
  return <>
    <section className="service-connect-fields" data-access-direction="outgoing">
      <div className="settings-card-head"><div><strong>{tx('outgoingTitle')}</strong><small>{tx('outgoingHelp')}</small></div></div>
      <MaskedKeyField direction="outgoing" label={tx('outgoingKey')} />
      <p className="service-connect-note">{tx('outgoingStored')}</p>
      <div className="settings-card-actions" data-replace-outgoing><Button variant="secondary" onClick={() => {}}>{tx('replaceKey')}</Button></div>
      <CapabilitiesResult />
    </section>
    <section className="service-connect-fields" data-access-direction="incoming" data-incoming-key-state="created">
      <div className="settings-card-head"><div><strong>{tx('incomingTitle')}</strong><small>{tx('incomingHelp')}</small></div></div>
      <MaskedKeyField direction="incoming" label={tx('incomingKey')} />
      <p className="service-connect-note">{tx('incomingStored')}</p>
      <div className="settings-card-actions" data-key-actions>
        <Button variant="secondary" onClick={() => {}}>{tx('replaceShort')}</Button>
        <Button variant="danger-outline" onClick={() => {}}>{tx('revokeShort')}</Button>
      </div>
      <p className="service-connect-note">{tx('revokeHint')}</p>
    </section>
  </>;
}
