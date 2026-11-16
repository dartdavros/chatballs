import { FormField } from '../../../../apps/internal-ui/src/shared/form-controls';
import { Button } from '../../../../apps/internal-ui/src/shared/ui-controls';
import { StatusPill } from '../../../../apps/internal-ui/src/shared/ui';
import { SavedServiceAccess } from './SavedServiceAccess';
import { tx } from './copy';

export function ConnectionReadyCard() {
  return <section className="administration-card" data-connection-state="ready" aria-labelledby="connection-title">
    <div className="service-connect-fields">
      <div className="settings-card-head service-card-title">
        <div><strong id="connection-title">{tx('connectionTitle')}</strong></div>
        <StatusPill status="healthy" label={tx('connectionReady')} />
      </div>
      <div className="administration-fields">
        <FormField label={tx('connectionName')} value={tx('connectionNameValue')} onChange={() => {}} />
        <FormField label={tx('serviceUrl')} value={tx('serviceUrlValue')} mono onChange={() => {}} />
      </div>
      <SavedServiceAccess />
    </div>
    <div className="administration-actions"><Button variant="primary" disabled>{tx('saveConnection')}</Button></div>
  </section>;
}
