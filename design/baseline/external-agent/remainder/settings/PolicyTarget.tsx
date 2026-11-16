import { FormField, SelectField } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { tx } from './copy';

// The shared connection can serve several agents; grants have an explicit individual target.
export function PolicyTarget({ disabled }: { disabled: boolean }) {
  return <div data-policy-agent="support" data-policy-connection="support-service">
    <div className="administration-fields">
      <FormField label={tx('policyConnection')} value={tx('nameValue')} />
      <SelectField label={tx('policyAgent')} value="support" disabled={disabled} onChange={() => {}}
        options={[["support", tx('supportAgent')], ["sales", tx('salesAgent')]]} />
    </div>
    <p className="settings-section-note">{tx('policyScope')}</p>
  </div>;
}
