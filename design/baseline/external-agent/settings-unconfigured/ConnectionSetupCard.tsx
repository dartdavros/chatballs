import { FormField } from '../../../../apps/internal-ui/src/shared/form-controls';
import { Button } from '../../../../apps/internal-ui/src/shared/ui-controls';
import { StatusPill } from '../../../../apps/internal-ui/src/shared/ui';
import { ServiceAccess } from './ServiceAccess';
import { tx } from './copy';

export function ConnectionSetupCard() {
  return <section className="administration-card" data-connection-form aria-labelledby="connection-title">
    <div className="service-connect-fields">
      <div className="settings-card-head service-card-title">
        <div><strong id="connection-title">{tx('connectionTitle')}</strong></div>
        <StatusPill status="unchecked" label={tx('notConfigured')} />
      </div>
      <div className="administration-fields">
        <FormField label={tx('connectionName')} value="" onChange={() => {}} />
        <FormField label={tx('serviceUrl')} value="" placeholder="https://…" mono onChange={() => {}} />
      </div>
      <ServiceAccess />
    </div>
    <div className="administration-actions">
      <Button variant="primary" disabled>{tx('saveConnection')}</Button>
    </div>
  </section>;
}
